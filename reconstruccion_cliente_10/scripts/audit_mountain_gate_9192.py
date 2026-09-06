"""Read-only native Return976 -> sphere2807 -> quest9115 closure."""
import csv
import hashlib
import json
import math
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/mountain-gate-9192'
CLIENT = ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575'
queries = {
    'return_point': 'select * from return_points where id=976',
    'skill_effects': 'select effect_id from skill_effects where skill_id=39534 order by id',
    'effects': 'select * from effects where id in (71839,73161)',
    'return_effect': 'select * from special_effects where id=37103',
    'objective': 'select * from quest_act_obj_interactions where id=1078',
    'next_accept': 'select * from quest_act_con_accept_spheres where id=926',
    'next_cinema': 'select * from quest_act_obj_cinemas where id=41',
    'next_components': 'select * from quest_components where quest_context_id=9115 order by id',
}
catalogs = {}
hashes = {}
for name, path in {
    'full': ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3',
    'retail': CLIENT / 'game/db/compact.sqlite3',
    'runtime': ROOT / 'server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3',
}.items():
    with path.open('rb') as stream:
        hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        catalogs[name] = {k: [dict(r) for r in db.execute(q)] for k,q in queries.items()}
assert catalogs['full'] == catalogs['retail'] == catalogs['runtime']
assert catalogs['full']['return_point'][0]['editor_name'] == 'metastasis_gate'
assert catalogs['full']['return_effect'][0]['value1'] == 976
assert catalogs['full']['next_accept'][0]['sphere_id'] == 2807

points = list(csv.DictReader((OUT/'native-return-points.csv').open(encoding='utf-8-sig')))
point, = [p for p in points if p['editor_name']=='metastasis_gate']
assert point['zone_id'] == '350'
zone, = [z for z in ET.parse(OUT/'world.xml').iter('Zone') if z.get('id')=='350']
origin = [int(zone.get('originX')), int(zone.get('originY'))]
assert origin == [17,28]
position = [origin[0]*1024+float(point['x']),origin[1]*1024+float(point['y']),float(point['z'])]
sphere = [17*1024+2447.54,28*1024+2378.86,506.922]
distance = math.dist(position,sphere)
assert distance < 10
for name in ['return_point.g','quest_area_sphere.g','world.xml']:
    hashes[name] = hashlib.sha256((OUT/name).read_bytes()).hexdigest()
report = {'quest':9192,'catalogs':catalogs,'sha256':hashes,'destination':{
    'id':976,'native':point,'origin_cell':[17,28],'world_position':position,
    'yaw_radians':float(point['z_rot']),'zone':350,'world':'main_world',
    'sphere':2807,'sphere_center':sphere,'radius':10,'distance':distance,
    'next_quest':9115,'cinema':290},'cause':'Return loader indexed Memory Tome destinations only; Return976 has no book binding',
    'recovery':'Already completed9192: one GM move to the exact native destination; no quest or reward edits'}
(OUT/'catalog-and-destination.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['destination']))
