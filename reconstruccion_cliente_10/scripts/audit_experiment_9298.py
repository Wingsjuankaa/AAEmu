"""Read-only r575 item -> requirements -> shared fountain area closure."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/experiment-9298'
QUERIES = {
    'item': 'select id,use_skill_id from items where id=46685',
    'requirements': "select * from unit_reqs where owner_type='Skill' and owner_id=40653 order by id",
    'sphere': 'select * from spheres where id=2836',
    'sphere_event': 'select * from sphere_quests where id=1637',
    'objective': 'select * from quest_act_obj_item_uses where id=964',
    'act': 'select * from quest_acts where quest_component_id=40452',
    'component': 'select * from quest_components where id=40452',
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
area_text = (OUT / 'quest_area_sphere.g').read_text()
area, = [block for block in area_text.split('area') if re.search(r'\bstype 2836\s', block)]
assert 'radius 12' in area
assert 'x 1594.94, y 2329.86, z 875.591' in area
sign_text = (OUT / 'quest_sign_sphere.g').read_text()
sign, = [block for block in sign_text.split('area') if re.search(r'\bctype 40452\s', block)]
assert 'qtype 9298' in sign and 'radius 8' in sign
for filename in ['quest_area_sphere.g', 'quest_sign_sphere.g']:
    hashes[filename] = hashlib.sha256((OUT / filename).read_bytes()).hexdigest()
report = {
    'catalogs': catalogs, 'sha256': hashes, 'queries': QUERIES,
    'zone': 354, 'native_area': area.strip(), 'quest_marker': sign.strip(),
    'cause': 'AreaSphere2836 was resolved via SphereQuest1637 -> quest9242 map markers, then filtered by quest9298 component40452; no match is possible.',
    'fix': 'Use the native stype2836 execution volume (radius12) in the current world; retain legacy component filtering only when native geometry is absent.',
    'acceptance': 'Pending retail use from accessible fountain edge; no client or database mutation.',
}
(OUT / 'native-contracts.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Full/retail/runtime contracts agree; native sphere2836 radius12, quest9298 marker radius8; client unchanged.')
