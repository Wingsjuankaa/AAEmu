"""Read-only AA10 comparison of completion cleanup and abandonment destruction."""
import json
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/quest-completion-item-retention'
TABLES = {
    'quest_act_obj_item_gathers': 'QuestActObjItemGather',
    'quest_act_supply_items': 'QuestActSupplyItem',
    'quest_act_con_accept_items': 'QuestActConAcceptItem',
}


def audit(path):
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    findings = []
    for table, detail_type in TABLES.items():
        findings += [dict(r, act_type=detail_type) for r in db.execute(f'''
            SELECT c.quest_context_id AS quest, c.id AS component,
                   d.id AS detail, d.item_id, d.cleanup, d.destroy_when_drop,
                   a.enable
            FROM {table} d
            JOIN quest_acts a ON a.act_detail_id=d.id AND a.act_detail_type=?
            JOIN quest_components c ON c.id=a.quest_component_id
            WHERE d.cleanup='f' AND d.destroy_when_drop='t'
            ORDER BY c.quest_context_id, d.id''', (detail_type,))]
    energy = [dict(r) for r in db.execute(
        'SELECT * FROM quest_act_obj_item_gathers WHERE id IN (4244,4245,4246)')]
    db.close()
    return dict(path=str(path), retention_contracts=findings, energy_gather_acts=energy)


def main():
    scope = json.loads((ROOT / 'forensics/output/aa10-client-forensics/hiram-onward-sweep/audit.json').read_text(encoding='utf-8'))
    quest_ids = {q['id'] for q in scope['quests']}
    full = audit(ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3')
    compact = audit(ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3')
    result = dict(full=full, compact=compact,
        scope_quests=sorted({r['quest'] for r in full['retention_contracts'] if r['quest'] in quest_ids}),
        scope_contracts=[r for r in full['retention_contracts'] if r['quest'] in quest_ids],
        classification='native retention contracts; not proof of retail completion for every quest')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'native-contracts.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(full_contracts=len(full['retention_contracts']),
        compact_contracts=len(compact['retention_contracts']), scope_quests=result['scope_quests'])))


if __name__ == '__main__':
    main()
