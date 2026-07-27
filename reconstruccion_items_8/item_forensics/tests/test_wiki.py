from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ..config import ForensicsConfig
from ..db import create_database, finalize_database
from ..util import sha256_file
from ..wiki import (
    DEFAULT_BASE_URL,
    audit_wiki,
    parse_wiki_page,
    scan_wiki,
    wiki_edge_ids,
    wiki_seed_ids,
    write_wiki_snapshot,
)


def item_page(
    item_id: int,
    name: str,
    *,
    level: int = 1,
    skill_id: int | None = None,
    craft_id: int | None = None,
) -> bytes:
    skill = (
        f'<a href="/na-en/db/skills/{skill_id}">Visible skill</a>'
        if skill_id
        else ""
    )
    craft = (
        f'<a href="/na-en/db/crafts/{craft_id}">Visible craft</a>'
        if craft_id
        else ""
    )
    return f"""
<!doctype html>
<html>
<head><title>{name} - Item - ArcheRage Wiki</title></head>
<body>
<nav><a href="/na-en/db/items/999">Navigation noise</a></nav>
<section>
  <div>ID: {item_id}</div>
  <div>Item</div>
  <div>Consumables &gt; Dye</div>
  <div>Grand</div>
  <h1>{name}</h1>
  <div>Level:</div><div>{level}</div>
  <div>Use:</div>
  {skill}
  {craft}
  <a href="/na-en/db/items/45632">Wrapped Dye Ticket</a>
  <a href="/na-en/db/maps/zone-5/doodad-14073">Map</a>
</section>
<footer>Archerage.to - the first ArcheAge Private Server</footer>
</body>
</html>
""".encode("utf-8")


class WikiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        repo = root / "repo"
        repo.mkdir()
        client = root / "client.sqlite"
        client.touch()
        runtime = root / "runtime.sqlite"
        runtime.touch()
        runtime_env = repo / ".env"
        runtime_env.write_text(f"COMPACT_DB={runtime}\n", encoding="utf-8")
        streams = root / "streams"
        streams.mkdir()
        output = root / "output"
        self.config = ForensicsConfig(
            client_build="Kakao 8.0.3.12 r558734",
            client_compact=client,
            streams_root=streams,
            repo_root=repo,
            legacy_item_root=repo,
            output_dir=output,
            runtime_env=runtime_env,
            runtime=runtime,
            sql_manifest=None,
            surface_manifest=None,
            gamepak_index=None,
            x2game=(),
        )
        connection = create_database(self.config.database)
        connection.executemany(
            """
            INSERT INTO items(
                item_id,impl_id,name,description,category_id,level,
                use_skill_id,buff_id,craft_id,loot_quest_id,
                client_row_json,client_provenance
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                (
                    100,
                    0,
                    "confirmed",
                    "",
                    1,
                    1,
                    0,
                    0,
                    0,
                    0,
                    "{}",
                    "client_compact_8",
                ),
                (
                    30280,
                    27,
                    "<ref:214551>",
                    "",
                    33,
                    1,
                    39137,
                    0,
                    0,
                    0,
                    "{}",
                    "client_compact_8",
                ),
                (
                    31789,
                    12,
                    "에아나드의 단검 제작 비법서",
                    "",
                    65,
                    1,
                    0,
                    0,
                    0,
                    0,
                    "{}",
                    "client_compact_8",
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO native_entities(
                entity_kind,entity_id,source_table,state,row_json,provenance,
                evidence_json
            ) VALUES ('craft',900,'crafts','confirmed','{}',
                      'game11_native','{}')
            """
        )
        connection.executemany(
            """
            INSERT INTO descriptors(
                item_id,family,table_name,row_key,descriptor_json,state,
                provenance,evidence_json
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                (100, "generic", None, "100", "{}", "confirmed", "native", "{}"),
                (30280, "dyeing", None, "30280", "{}", "unknown", "native", "{}"),
                (31789, "recipe", None, "31789", "{}", "missing", "native", "{}"),
            ),
        )
        finalize_database(connection)
        connection.close()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_parser_ignores_navigation_and_recovers_visible_relations(self) -> None:
        parsed = parse_wiki_page(
            item_page(30280, "Red Rose Dye", skill_id=39137),
            entity_kind="items",
            entity_id=30280,
            locale="na-en",
        )
        self.assertEqual(parsed.parse_state, "confirmed")
        self.assertEqual(parsed.name, "Red Rose Dye")
        self.assertEqual(parsed.level, 1)
        targets = {(link.kind, link.entity_id) for link in parsed.links}
        self.assertNotIn(("items", "999"), targets)
        self.assertIn(("skills", "39137"), targets)
        self.assertIn(("items", "45632"), targets)
        self.assertEqual(parsed.map_links, ("/na-en/db/maps/zone-5/doodad-14073",))

    def test_seed_scope_selects_only_unresolved_descriptors(self) -> None:
        self.assertEqual(
            wiki_seed_ids(self.config.database, scope="unresolved"),
            [30280, 31789],
        )
        self.assertEqual(
            wiki_seed_ids(
                self.config.database,
                scope="all",
                explicit_ids=(31789, 30280, -1, 30280),
            ),
            [30280, 31789],
        )

    def test_scan_is_resumable_and_audit_is_deterministic(self) -> None:
        calls: list[str] = []

        def fetch(url: str) -> tuple[int, bytes, str]:
            calls.append(url)
            if url.endswith("/robots.txt"):
                return 200, b"User-agent: *\nCrawl-delay: 1\n", "text/plain"
            if url.endswith("/items/30280"):
                return (
                    200,
                    item_page(30280, "Red Rose Dye", skill_id=39137),
                    "text/html",
                )
            raise AssertionError(url)

        with patch(
            "reconstruccion_items_8.item_forensics.wiki.time.sleep",
            return_value=None,
        ):
            first = scan_wiki(
                self.config,
                explicit_ids=(30280,),
                fetcher=fetch,
            )
            second = scan_wiki(
                self.config,
                explicit_ids=(30280,),
                fetcher=fetch,
            )
        self.assertEqual(first["downloaded"], 1)
        self.assertEqual(second["downloaded"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(len(calls), 3)

        write_wiki_snapshot(
            self.config.wiki_cache_dir,
            base_url=DEFAULT_BASE_URL,
            locale="na-en",
            entity_kind="items",
            entity_id=31789,
            status_code=200,
            payload=item_page(31789, "Ayanad Dagger Design", craft_id=900),
        )
        first_audit = audit_wiki(self.config)
        first_hash = sha256_file(self.config.wiki_database)
        second_audit = audit_wiki(self.config)
        second_hash = sha256_file(self.config.wiki_database)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(
            first_audit["database_sha256"],
            second_audit["database_sha256"],
        )

        connection = sqlite3.connect(self.config.wiki_database)
        states = {
            (row[0], row[1]): row[2]
            for row in connection.execute(
                """
                SELECT entity_id,field_name,state
                FROM wiki_assertions
                """
            )
        }
        self.assertEqual(
            states[(30280, "name")],
            "external_resolves_opaque",
        )
        self.assertEqual(states[(30280, "use_skill_id")], "exact_match")
        self.assertEqual(
            wiki_edge_ids(
                self.config.wiki_database,
                entity_kind="skills",
            ),
            [39137],
        )
        self.assertEqual(
            connection.execute(
                """
                SELECT state FROM wiki_edges
                WHERE src_kind='items' AND src_id=31789
                  AND dst_kind='crafts' AND dst_id='900'
                """
            ).fetchone()[0],
            "native_match",
        )
        evidence = json.loads(
            connection.execute(
                """
                SELECT evidence_json FROM wiki_assertions
                WHERE entity_id=30280 AND field_name='use_skill_id'
                """
            ).fetchone()[0]
        )
        self.assertFalse(evidence["authority"])
        self.assertEqual(
            connection.execute("PRAGMA quick_check").fetchone()[0],
            "ok",
        )
        connection.close()


if __name__ == "__main__":
    unittest.main()
