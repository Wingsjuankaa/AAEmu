"""Classify quest suppliers against native Zone spawners, proxies and item data."""
import csv
import json
import re
import sqlite3
from audit_hiram_onward_quests import ROOT, OUT, rows


def main():
    report = json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
    db = sqlite3.connect((ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3').as_uri()+'?mode=ro',uri=True)
    db.row_factory = sqlite3.Row
    spawner_entries = {}
    for path in (OUT/'npc-native').rglob('npc_spawners.g'):
        for type_id in set(map(int,re.findall(r'(?m)^\s*spawnerType\s+(\d+)',path.read_text(encoding='utf-8-sig')))):
            spawner_entries.setdefault(type_id,[]).append(str(path.relative_to(OUT/'npc-native')))
    npc_findings = []
    for template, quests in report['npcs'].items():
        npc_id = int(template)
        members = rows(db,'SELECT npc_spawner_id FROM npc_spawner_npcs WHERE member_type="Npc" AND member_id=?',(npc_id,))
        members += rows(db, 'SELECT s.npc_spawner_id FROM npc_spawner_npcs s JOIN npc_group_members g ON g.npc_group_id=s.member_id WHERE s.member_type="NpcGroup" AND g.npc_id=?', (npc_id,))
        entries = sorted({entry for r in members for entry in spawner_entries.get(r['npc_spawner_id'],[])})
        proxies = rows(db,'SELECT id FROM doodad_almighties WHERE model=? UNION SELECT doodad_almighty_id AS id FROM doodad_func_groups WHERE model=?',(f'npctype://{npc_id}',f'npctype://{npc_id}'))
        dynamic = rows(db,'SELECT id FROM spawn_effects WHERE owner_type_id=1 AND sub_type=?',(npc_id,))
        npc_findings.append(dict(npc=npc_id,quests=quests,native_zone_entries=entries,proxy_templates=proxies,
            dynamic_spawn_effects=dynamic,status='native_zone_spawner' if entries else ('proxy_or_dynamic' if proxies or dynamic else 'no_static_source_proven')))
    item_findings = []
    for template, quests in report['items'].items():
        item_id = int(template)
        loots = rows(db,'SELECT id,loot_pack_id,min_amount,max_amount,drop_rate FROM loots WHERE item_id=?',(item_id,))
        supplies = rows(db,'SELECT id FROM quest_act_supply_items WHERE item_id=?',(item_id,))
        loot_funcs = rows(db,'SELECT id FROM doodad_func_loot_items WHERE item_id=?',(item_id,))
        special = rows(db,'SELECT id,special_effect_type_id FROM special_effects WHERE special_effect_type_id=27 AND value1=?',(item_id,))
        crafts = rows(db,'SELECT craft_id FROM craft_products WHERE item_id=?',(item_id,))
        skill_products = rows(db,'SELECT * FROM skill_products WHERE item_id=?',(item_id,))
        item_findings.append(dict(item=item_id,quests=quests,loot_entries=loots,quest_supply_details=supplies,
            doodad_loot_functions=loot_funcs,special_item_effects=special,crafts=crafts,skill_products=skill_products,status='supplier_metadata_present' if loots or supplies or loot_funcs or special or crafts or skill_products else 'other_supplier_requires_review'))
    per_quest = []
    for quest in report['quests']:
        quest_id = quest['id']
        actors = [r for r in report['actors'] if quest_id in r['quests']]
        per_quest.append(dict(**quest,static_doodads=[r['id'] for r in actors if r['placements']],
            instance_doodads=[r['id'] for r in actors if r['instance_worlds']],
            no_world_placement=[r['id'] for r in actors if not r['placements'] and not r['instance_worlds']],
            npcs=[r['npc'] for r in npc_findings if quest_id in r['quests']],items=[r['item'] for r in item_findings if quest_id in r['quests']],
            acceptance='static_audit_only_not_retail_completed'))
    result=dict(npcs=npc_findings,items=item_findings,quests=per_quest)
    (OUT/'supplier-coverage.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    with (OUT/'quest-coverage.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=per_quest[0].keys());writer.writeheader()
        for quest in per_quest:
            writer.writerow({k:','.join(map(str,v)) if isinstance(v,list) else v for k,v in quest.items()})
    from collections import Counter
    print('NPC:',dict(Counter(r['status'] for r in npc_findings)))
    print('Items:',dict(Counter(r['status'] for r in item_findings)))


if __name__=='__main__':
    main()
