"""Read-only AA10 Ipnya catalog audit. No runtime or package writes.

Run after PakBatchExtract using the frontier entries.txt. Output is deterministic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path('E:/AAEmu/rama_10')
REPO = ROOT / 'server/AAEmu'
FRONTIER = ROOT / 'forensics/output/aa10-client-forensics/ipnya-slot-reinforce-frontier'
TABLES = ['equip_slot_reinforces', 'equip_slot_reinforce_materials',
          'equip_slot_reinforce_level_effects', 'equip_slot_reinforce_unit_modifiers',
          'equip_slot_reinforce_set_effects', 'equip_slot_reinforce_bundle_effects',
          'enum_equip_slot_reinforce_attributes']


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def audit(path):
    c = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    def rows(sql, args=()):
        return [dict(r) for r in c.execute(sql, args)]
    tables = {r['name'] for r in c.execute("select name from sqlite_master where type='table'")}
    result = {'path': str(path), 'sha256': sha(path), 'quick_check': c.execute('pragma quick_check').fetchone()[0], 'tables': {}}
    for table in TABLES:
        if table not in tables:
            result['tables'][table] = {'missing': True}
            continue
        data = rows('select * from ' + table + ' order by id')
        mechanics = [{k: v for k, v in r.items() if k not in ('name', 'desc')} for r in data]
        result['tables'][table] = {'count': len(data), 'rows_sha256': digest(data), 'mechanics_sha256': digest(mechanics), 'rows': data}
    result['configs'] = rows('select * from content_configs where id in (236,237,359,360) order by id')
    if 'enum_content_configs' in tables:
        result['config_names'] = rows('select * from enum_content_configs where id in (236,237,359,360) order by id')
    result['slots'] = rows('select slot_type_id,min(level) min_level,max(level) max_level,count(*) rows,sum(need_exp) sum_catalog_need_exp from equip_slot_reinforces group by slot_type_id order by slot_type_id')
    result['enum_slots'] = rows('select * from enum_equip_slot order by id') if 'enum_equip_slot' in tables else []
    result['special_effects'] = rows('select * from special_effects where special_effect_type_id in (161,163) order by id')
    result['skill_links'] = rows("select se.* from skill_effects se join effects e on e.id=se.effect_id join special_effects sp on sp.id=e.actual_id where e.actual_type='SpecialEffect' and sp.special_effect_type_id in (161,163) order by se.id")
    ids = sorted({r['skill_id'] for r in result['skill_links']} | {38363,38664})
    result['skills'] = rows('select id,name,casting_time,cooldown_time,consume_lp,target_type_id,target_selection_id from skills where id in ('+','.join(map(str,ids))+') order by id')
    result['materials'] = rows('select distinct si.* from item_set_items si join equip_slot_reinforce_materials m on m.need_material_item_set_id=si.item_set_id order by si.id')
    item_ids = sorted({r['item_id'] for r in result['materials']} | {46682,51597} | {r['level_up_item_id'] for r in result['tables']['equip_slot_reinforces']['rows'] if r['level_up_item_id']})
    result['items'] = rows('select id,name,use_skill_id,craft_id,level_requirement,max_stack_size from items where id in ('+','.join(map(str,item_ids))+') order by id')
    result['missing_item_ids'] = sorted(set(item_ids)-{r['id'] for r in result['items']})
    result['orphan_material_sets'] = rows('select m.id,m.need_material_item_set_id from equip_slot_reinforce_materials m left join item_sets s on s.id=m.need_material_item_set_id where m.need_material_item_set_id<>0 and s.id is null')
    result['orphan_level_effects'] = rows('select m.id from equip_slot_reinforce_unit_modifiers m left join equip_slot_reinforce_level_effects e on e.id=m.equip_slot_reinforce_level_effect_id where e.id is null')
    result['material_require_levels'] = rows('select require_level,count(*) n from equip_slot_reinforce_materials group by require_level order by require_level')
    result['acquisition_catalog_links'] = {}
    for table in ['craft_products', 'merchant_goods']:
        if table in tables:
            result['acquisition_catalog_links'][table] = rows('select * from '+table+' where item_id in ('+','.join(map(str,item_ids))+') order by id')
    if 'localized_texts' in tables:
        cols = [r['name'] for r in c.execute('pragma table_info(localized_texts)')]
        result['localized_text_columns'] = cols
        if {'tbl_name','tbl_column_name','idx','en_us'} <= set(cols):
            result['item_names_en_us'] = rows("select idx,en_us from localized_texts where tbl_name='items' and tbl_column_name='name' and idx in ("+','.join(map(str,item_ids))+') order by idx')
    c.close()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=FRONTIER/'catalog-audit.json')
    args = parser.parse_args()
    paths = {
        'full': ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3',
        'reference_embedded': FRONTIER/'reference/db/compact.sqlite3',
        'primary_embedded': FRONTIER/'primary/db/compact.sqlite3',
        'primary_loose': ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/game/db/compact.sqlite3',
        'server_runtime': REPO/'.server_files/AAEmu.Game/Data/compact.sqlite3',
    }
    output = {'schema': 1, 'scope': 'Ipnya slot reinforce; read only', 'databases': {name:audit(path) for name,path in paths.items()}}
    output['table_comparison'] = {t: {name:{k:v for k,v in db['tables'][t].items() if k!='rows'} for name,db in output['databases'].items()} for t in TABLES}
    output['client_entries'] = []
    for p in sorted((FRONTIER/'primary').rglob('*')):
        if p.is_file() and p.suffix in ('.lua','.alb'):
            rel=p.relative_to(FRONTIER/'primary')
            original=FRONTIER/'reference'/rel
            output['client_entries'].append({'entry':'game/'+rel.as_posix(),'primary_sha256':sha(p),'reference_sha256':sha(original),'equal':sha(p)==sha(original)})
    # Ghidra project is an earlier release identity: never silently reuse its RVAs.
    import pefile
    dll = ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/Bin64/x2game.dll'
    pe = pefile.PE(str(dll))
    output['native_reanchor'] = {'path':str(dll), 'sha256':sha(dll), 'machine':hex(pe.FILE_HEADER.Machine), 'image_base':hex(pe.OPTIONAL_HEADER.ImageBase), 'functions':[]}
    for path in sorted(FRONTIER.glob('native*/*.bytes')):
        matches=[]
        for line in path.read_text().splitlines():
            rva, hexbytes=line.split(); expected=bytes.fromhex(hexbytes)
            matches.append({'rva':hex(int(rva)), 'length':len(expected), 'exact_match':pe.get_data(int(rva),len(expected))==expected})
        output['native_reanchor']['functions'].append({'evidence':str(path),'ranges':matches,'all_match':all(r['exact_match'] for r in matches)})
    pe.close()
    zone = ROOT/'artifacts/native/x2game-dev_dedicate.dll'
    zone_pe = pefile.PE(str(zone))
    output['zone_native_reanchor'] = {'path':str(zone), 'sha256':sha(zone), 'machine':hex(zone_pe.FILE_HEADER.Machine), 'functions':[]}
    for va in ('3936b560','3936b3c0'):
        path=FRONTIER/'zone-unitstate'/(va+'.bytes')
        matches=[]
        for line in path.read_text().splitlines():
            rva,hexbytes=line.split();expected=bytes.fromhex(hexbytes)
            matches.append({'rva':hex(int(rva)), 'length':len(expected), 'exact_match':zone_pe.get_data(int(rva),len(expected))==expected})
        output['zone_native_reanchor']['functions'].append({'evidence':str(path), 'ranges':matches,'all_match':all(x['exact_match'] for x in matches)})
    zone_pe.close()
    output['native_reroll_rule']={}
    for name,path in paths.items():
        conn=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
        output['native_reroll_rule'][name]=conn.execute("select id,key,text from ui_texts where id=9256").fetchall()
        conn.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.out),'sha256':sha(args.out),'counts':{t:output['databases']['full']['tables'][t]['count'] for t in TABLES}}))


if __name__ == '__main__':
    main()
