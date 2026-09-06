"""Read-only AA10 closure for Alcos' personal interaction -> report phase."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/holy-soldiers-9191'
OUT.mkdir(parents=True, exist_ok=True)
CLIENT = ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575'
sources = {
    'full': ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3',
    'retail': CLIENT / 'game/db/compact.sqlite3',
    'runtime': ROOT / 'server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3',
}
queries = {
    'objectives': 'select * from quest_act_obj_interactions where id in (1077,1080)',
    'recipient': 'select * from quest_act_con_report_doodads where id=105',
    'functions': 'select * from doodad_funcs where doodad_func_group_id in (38981,38982,39004,39007)',
    'phase_functions': 'select * from doodad_phase_funcs where doodad_func_group_id in (38981,38982,39004,39007)',
    'use': 'select * from doodad_func_uses where id=9972',
    'quests': 'select * from doodad_func_quests where id in (1169,1170)',
    'reacts': 'select * from doodad_func_quest_reacts where id in (153,154,174,178,179,224,305,306)',
    'template': 'select * from doodad_almighties where id=13447',
}
catalogs = {}
hashes = {}
for name, path in sources.items():
    with path.open('rb') as f:
        hashes[name] = hashlib.file_digest(f, 'sha256').hexdigest()
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        catalogs[name] = {key: [dict(row) for row in db.execute(sql)] for key, sql in queries.items()}
    objective = catalogs[name]['objectives'][1]
    assert objective['doodad_id'] == 13447 and objective['highlight_doodad_phase'] == 39004
    use = next(f for f in catalogs[name]['functions'] if f['id'] == 35810)
    assert use['actual_func_type'] == 'DoodadFuncUse' and use['next_phase'] == 39007
    assert use['func_skill_id'] == 40100 and use['act_count'] == 0

assert catalogs['full'] == catalogs['retail'] == catalogs['runtime']
dll = CLIENT / 'Bin64/x2game.dll'
with dll.open('rb') as f:
    hashes['x2game.dll'] = hashlib.file_digest(f, 'sha256').hexdigest()
report = {
    'quest': 9191, 'catalogs': catalogs, 'sha256': hashes,
    'native': {
        'architecture': 'x64', 'image_base': '0x39000000', 'opcode': '0x151',
        'registration_rva': '0x3ebd60', 'handler_rva': '0x33d660',
        'lookup_rva': '0xf04a0', 'change_phase_rva': '0x6f5950',
        'serializer_rva': '0xa9e750',
        'body': 'bc objId, u32 phase, i32 data, u32 growing, i32 puzzleGroup, u32 item, bool isGoods=false',
        'negative': 'SCDoodadHit follows function type 0x0e (SkillHit); it is not the Use acknowledgement.',
    },
    'observed': {'utc': '2026-09-04T16:18:51Z', 'obj_id': 101267,
                 'shared_phase': 38981, 'personal_phase': 39004, 'skill': 40100,
                 'quest_status': 'Ready', 'objective_index_1': 1},
}
(OUT / 'catalog-and-native.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'output': str(OUT), 'catalogs_equal': True, 'quest': 9191}))
