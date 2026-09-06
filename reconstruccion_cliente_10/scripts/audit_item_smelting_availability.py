"""Read-only, deterministic audit of the exact AA10 Smelting data frontier.

No runtime/database mutations. Output is a report, not a deployable catalogue.
Run twice to separate deterministic evidence from interpretation.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sqlite3


SOURCES = {
    "full": ("data/sqlite/authoritative/game_decrypted.sqlite3", "87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f"),
    "retail_snapshot": ("data/sqlite/retail/compact.sqlite3", "f8c7a0268a26d4efaec47a2a2b1b525447bf16c274506cd97bf571839b5e6d29"),
    "runtime_snapshot": ("data/sqlite/runtime/compact.sqlite3", "fb9273ae82f69fafcf5ff94e2ff95d7bbcb29a3ad3f6502caf05713251bafdaf"),
    "client_current": ("client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3", "f61b6b6ed23ad83403d0e45f7d72f7cdf33553bcde03535e800acbb84639165b"),
}
QUERIES = {
    "catalogue_counts": "SELECT (SELECT count(*) FROM items) items, (SELECT count(*) FROM item_smeltings) recipes, (SELECT count(*) FROM item_smelting_items) outputs",
    "items": "SELECT id,name,description,use_skill_id FROM items WHERE id IN (40000,43445,43446,43476,43482,43489) ORDER BY id",
    "recipes": "SELECT * FROM item_smeltings ORDER BY id",
    "outputs": "SELECT * FROM item_smelting_items ORDER BY id",
    "probabilities": "SELECT * FROM item_smelting_probs ORDER BY id",
    "missing_targets": "SELECT s.id recipe,s.item_id FROM item_smeltings s LEFT JOIN items i ON i.id=s.item_id WHERE i.id IS NULL ORDER BY s.id",
    "missing_outputs": "SELECT s.id output_row,s.item_smelting_id recipe,s.item_id FROM item_smelting_items s LEFT JOIN items i ON i.id=s.item_id WHERE i.id IS NULL ORDER BY s.id",
    "duplicate_selector_keys": "SELECT item_id,amount,count(*) candidates FROM item_smeltings GROUP BY item_id,amount HAVING count(*)>1 ORDER BY item_id,amount",
    "skill_effect_chain": "SELECT s.id skill_effect_row,s.skill_id,s.effect_id,e.actual_type,e.actual_id,x.special_effect_type_id,x.value1,x.value2,x.value3,x.value4,x.value5,x.value6,x.value7 FROM skill_effects s JOIN effects e ON e.id=s.effect_id LEFT JOIN special_effects x ON e.actual_type='SpecialEffect' AND x.id=e.actual_id WHERE s.skill_id IN (35525,37020) ORDER BY s.id",
    "localized_items": "SELECT idx,tbl_column_name,en_us FROM localized_texts WHERE tbl_name='items' AND idx IN (40000,43445,43446,43476,43482,43489) ORDER BY idx,tbl_column_name",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(root):
    report = {"schema_version": 1, "target": "AA10 Returns 10.0.2.13 r575", "sources": {}, "queries": QUERIES}
    for label, (relative, expected) in SOURCES.items():
        path = root / relative
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"Source identity changed: {label}: {actual}")
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            db.row_factory = sqlite3.Row
            checks = {check: [row[0] for row in db.execute(f"PRAGMA {check}")]
                      for check in ("quick_check", "integrity_check")}
            if any(result != ["ok"] for result in checks.values()):
                raise ValueError(f"Integrity failure: {label}: {checks}")
            facts, unavailable = {}, {}
            for name, sql in QUERIES.items():
                try:
                    facts[name] = [dict(row) for row in db.execute(sql)]
                except sqlite3.OperationalError as error:
                    # Projection omissions are evidence; never substitute full rows.
                    if not str(error).startswith("no such table: "):
                        raise
                    facts[name] = None
                    unavailable[name] = str(error)
        if digest(path) != actual:
            raise ValueError(f"Source changed during audit: {label}")
        report["sources"][label] = {"path": relative, "sha256": actual, "checks": checks, "facts": facts, "unavailable": unavailable}
    report["conclusions"] = {
        "status": "blocked_not_playable_native_acceptance",
        "missing_output_templates": [43482, 43489],
        "client_missing_target": 40000,
        "correction": "35525 -> skill_effect 48479 -> effect 61510 -> SpecialEffect 27384 -> type 151 (not Anim 34)",
        "obsolete_catalyst_chain": "43445 -> skill 37020 -> effect 67866 -> SpecialEffect 31887 -> type 100, value1 1400",
        "not_proven": ["Historical removal date for this exact Returns build", "Restorable definitions for 43482/43489", "Native UI reachability of recipe 5", "Runtime transaction acceptance"],
        "no_mutation": "Do not remap recipe 29, fabricate templates or enable feature178 based on this report.",
    }
    # These are assertions about this frozen frontier, not general game rules.
    for source in report["sources"].values():
        facts = source["facts"]
        assert facts["catalogue_counts"][0]["recipes"] == 32
        assert len(facts["missing_outputs"]) == 8
        assert {r["item_id"] for r in facts["missing_outputs"]} == {43482, 43489}
        assert {r["item_id"] for r in facts["recipes"]} == {40000}
        chain = next(r for r in facts["skill_effect_chain"] if r["skill_id"] == 35525)
        assert (chain["actual_type"], chain["special_effect_type_id"]) == ("SpecialEffect", 151)
    assert len(report["sources"]["client_current"]["facts"]["missing_targets"]) == 32
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("E:/AAEmu/rama_10"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    payload = json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "audit.json").write_text(payload, encoding="utf-8")
    view = '<!doctype html><meta charset="utf-8"><title>AA10 Item Smelting audit</title>'
    view += '<h1>Item Smelting: no aceptado para juego</h1><p>Datos exactos; sin cambios de runtime.</p>'
    view += '<pre>' + html.escape(payload) + '</pre>'
    (args.output / "index.html").write_text(view, encoding="utf-8")
    print(json.dumps({"audit_sha256": digest(args.output / "audit.json"), "sources": len(report["sources"]), "integrity": "ok"}))


if __name__ == "__main__":
    main()
