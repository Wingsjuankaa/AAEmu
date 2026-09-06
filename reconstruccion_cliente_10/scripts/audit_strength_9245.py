"""Read-only r575 workbench interaction closure; no client or runtime DB edits."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/strength-9245'
QUERIES = {
    'item': 'select id,use_skill_id from items where id=46658',
    'skill': 'select id,target_type_id,target_selection_id,target_area_radius,target_area_count,casting_time from skills where id=40467',
    'effect_link': 'select * from skill_effects where skill_id=40467',
    'effect': 'select * from effects where id=73895',
    'interaction': 'select * from interaction_effects where id=7544',
    'requirements': "select * from unit_reqs where owner_type='Skill' and owner_id=40467",
    'reagents': 'select * from skill_reagents where skill_id=40467',
    'doodad': 'select id,once_one_man from doodad_almighties where id=13571',
    'function': 'select * from doodad_funcs where id=37422',
    'fake_use': 'select * from doodad_func_fake_uses where id=3712',
    'phases': 'select * from doodad_func_groups where doodad_almighty_id=13571 order by id',
    'phase_functions': 'select * from doodad_phase_funcs where doodad_func_group_id in (39797,39798) order by id',
    'objective': 'select * from quest_act_obj_interactions where id=1105',
    'acts': 'select * from quest_acts where quest_component_id in (select id from quest_components where quest_context_id=9245) order by id',
}
catalogs = {}
hashes = {}
for name, path in {
    'full': ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3',
    'retail': ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3',
    'runtime': ROOT / 'server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3',
}.items():
    with path.open('rb') as stream:
        hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        catalogs[name] = {key: [dict(row) for row in db.execute(sql)] for key, sql in QUERIES.items()}
assert catalogs['full'] == catalogs['retail'] == catalogs['runtime']
assert catalogs['full']['skill'][0]['target_area_radius'] == 20
assert catalogs['full']['function'][0]['next_phase'] == 39798
report = {'catalogs': catalogs, 'sha256': hashes, 'queries': QUERIES,
    'cause': 'GetAround excludes center; Target selection2 never re-added selected Doodad13571. Use effect ran on nearby non-doodad units, so no phase or quest event.',
    'fix': 'Include the selected doodad in Target-centered Doodad AoE before existing relation filtering, deduplication and target count cap.',
    'classification': 'server-required', 'acceptance': 'pending retail F interaction'}
(OUT / 'native-contracts.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('All 14 full/retail/runtime queries agree. Workbench13571 -> skill40467 -> effect73895/7544 -> Use19 -> phase39798.')
