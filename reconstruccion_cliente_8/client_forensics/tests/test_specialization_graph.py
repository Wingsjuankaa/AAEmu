from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from client_forensics.config import load_config
from client_forensics.specialization_graph import (
    _snapshot_valid,
    _write_snapshot,
    parse_specialization_skill_page,
    resolve_specialization,
    resolve_specialization_suite,
    specialization_paths,
    specialization_suite_paths,
)


STEALTH = b"""<!doctype html><html><head>
<title>Stealth - Skill - ArcheRage Wiki</title></head><body>
<nav><a href='/na-en/db/skills/99999'>Navigation</a></nav>
<main><h2>Skills &gt; Stealth</h2><div class='skill-detail'>
<div>ID: 10082</div><div>Skill</div><div>Shadowplay</div>
<div>Stealth (Rank 4)</div><div>Mana: 83</div><div>Range: Caster Only</div>
<div>Effect Granted: Invisible for up to 45 sec.</div>
<table><tr><th>ID</th><th>Name</th></tr>
<tr><td><a href='/na-en/db/skills/599'>599</a></td><td>Stealth (Rank 1)</td></tr>
<tr><td><a href='/na-en/db/skills/8225'>8225</a></td><td>Stealth (Rank 4)</td></tr>
</table></div></main></body></html>"""


class SpecializationIdentityTests(unittest.TestCase):
    def test_slug_name_and_id_resolve_to_same_ability(self) -> None:
        values = [resolve_specialization(value) for value in ("shadowplay", "Shadowplay", "8")]
        self.assertEqual({value.ability_id for value in values}, {8})
        self.assertEqual({value.slug for value in values}, {"shadowplay"})

    def test_unknown_specialization_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_specialization("not-a-skillset")

    def test_suite_resolves_all_or_a_deduplicated_ordered_selection(self) -> None:
        self.assertEqual(tuple(range(1, 15)), tuple(row.ability_id for row in resolve_specialization_suite()))
        selected = resolve_specialization_suite("shadowplay,2,Shadowplay,swiftblade")
        self.assertEqual((2, 8, 12), tuple(row.ability_id for row in selected))

    def test_suite_paths_are_stable(self) -> None:
        paths = specialization_suite_paths(load_config())
        self.assertEqual("specialization-suite-v1.json", paths["index"].name)
        self.assertEqual("specialization-suite-v1.manifest.json", paths["manifest"].name)


class SpecializationWikiParserTests(unittest.TestCase):
    def test_stealth_preserves_rank_variants_and_ignores_navigation(self) -> None:
        page = parse_specialization_skill_page(STEALTH, skill_id=10082)
        self.assertEqual(page.parse_state, "confirmed")
        self.assertEqual(page.name, "Stealth")
        self.assertEqual(page.ability, "Shadowplay")
        self.assertEqual(page.rank, 4)
        self.assertEqual(page.mana, 83)
        self.assertEqual(page.range_text, "Caster Only")
        self.assertEqual(page.sections["combo"], "not_present")
        self.assertEqual(
            [(row.relation, row.dst_id) for row in page.relations],
            [("variant_skill", 599), ("variant_skill", 8225)],
        )

    def test_combo_and_typed_links_remain_corroborative_records(self) -> None:
        payload = b"""<html><head><title>Attack - Skill - ArcheRage Wiki</title></head>
        <body><div><p>ID: 50</p><p>Shadowplay Attack (Rank 1)</p>
        <p>Combos: Deals more damage after <a href='/na-en/db/skills/51'>Mark</a></p>
        <p>Effect Granted: <a href='/na-en/db/buffs/70'>Marked</a></p></div></body></html>"""
        page = parse_specialization_skill_page(payload, skill_id=50)
        self.assertEqual(page.sections["combo"], "present")
        self.assertEqual(
            {(row.relation, row.dst_kind, row.dst_id) for row in page.relations},
            {("combo_skill", "skill", 51), ("effect_buff", "buff", 70)},
        )

    def test_parse_failure_and_missing_sections_are_explicit(self) -> None:
        page = parse_specialization_skill_page(b"<html><title>Missing</title></html>", skill_id=7)
        self.assertEqual(page.parse_state, "parse_failed")
        self.assertEqual(page.sections, {"effect": "not_present", "combo": "not_present", "variants": "not_present"})


class SpecializationSnapshotTests(unittest.TestCase):
    def test_snapshot_identity_and_hash_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            metadata = _write_snapshot(
                cache,
                skill_id=10082,
                canonical_url="https://example/na-en/db/skills/10082",
                status_code=200,
                payload=STEALTH,
                content_type="text/html",
                final_url="https://example/na-en/db/skills/10082",
                locale="na-en",
                error=None,
            )
            self.assertEqual(metadata["page_state"], "confirmed")
            self.assertTrue(_snapshot_valid(cache, 10082))
            path = cache / "10082.meta.json"
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["entity_id"] = 1
            path.write_text(json.dumps(changed), encoding="utf-8")
            self.assertFalse(_snapshot_valid(cache, 10082))


class ShadowplayArtifactTests(unittest.TestCase):
    def test_built_artifact_keeps_wiki_10082_outside_native_roots(self) -> None:
        config = load_config()
        path = specialization_paths(config, resolve_specialization("shadowplay"))["database"]
        if not path.is_file():
            self.skipTest("Shadowplay specialization artifact has not been built")
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM specialization_roots WHERE root_kind='skill'").fetchone()[0], 28)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM specialization_roots WHERE root_kind='passive_buff'").fetchone()[0], 6)
            self.assertEqual(connection.execute("SELECT root_member FROM specialization_skills WHERE skill_id=10082").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM specialization_roots WHERE root_kind='skill' AND native_id=36594").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM validation_events WHERE state<>'confirmed'").fetchone()[0], 0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
