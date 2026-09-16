"""Read-only verification of the Nuia overlay in source and mounted runtime."""
import csv
import json
import struct
import sqlite3
from itertools import product
from math import floor
from collections import defaultdict

from build_nuia_sidequest_placements import AUDIT, OUT, OVERLAY, REPO, read_json, sha


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def position(row):
    return tuple(f32(row['Position'][axis]) for axis in ('X', 'Y', 'Z'))


def near(a, b):
    return all(abs(x-y) < 0.01 for x, y in zip(a, b))


def verify(folder, valid_ids):
    expected = read_json(REPO/'AAEmu.Game/Data/Worlds/main_world'/OVERLAY)
    assert sha(folder/OVERLAY) == sha(REPO/'AAEmu.Game/Data/Worlds/main_world'/OVERLAY)
    rules = read_json(folder/'doodad_spawn_replacements.json')
    loaded = defaultdict(list)
    cells = defaultdict(list)
    suppressed = defaultdict(int)
    skipped_templates = 0
    for path in sorted(folder.glob('doodad_spawns*.json'), reverse=True):
        for row in read_json(path):
            p = row['Position']
            if any(rule['SourceFile'] == path.name and
                   (folder/rule['ReplacementFile']).is_file() and
                   rule['MinX'] <= p['X'] < rule['MaxX'] and
                   rule['MinY'] <= p['Y'] < rule['MaxY'] for rule in rules):
                suppressed[path.name] += 1
                continue
            if row['UnitId'] not in valid_ids:
                skipped_templates += 1
                continue
            coordinates = position(row)
            cell = tuple(map(floor, coordinates))
            # Spatial buckets preserve the loader's 0.01 tolerance without a
            # quadratic scan through every instance of a common world prop.
            neighbors = ((row['UnitId'], *(cell[i]+d[i] for i in range(3)))
                         for d in product((-1, 0, 1), repeat=3))
            if not any(near(coordinates, old) for key in neighbors for old in cells[key]):
                loaded[row['UnitId']].append(row)
                cells[(row['UnitId'], *cell)].append(coordinates)
    for row in expected:
        matches = [old for old in loaded[row['UnitId']] if near(position(row), position(old))]
        assert len(matches) == 1, (row, matches)
        # The native overlay must win over any near legacy duplicate.
        assert matches[0]['Position'] == row['Position']
        assert matches[0]['FuncGroupId'] == row['FuncGroupId']
        assert matches[0]['Scale'] == row['Scale']
    assert len(loaded[2853]) == 5
    return dict(overlay_sha256=sha(folder/OVERLAY), checked_placements=len(expected),
                boats=len(loaded[2853]), effective_catalog_rows=sum(map(len, loaded.values())),
                suppressed=dict(suppressed), skipped_missing_template_rows=skipped_templates)


def main():
    compact = REPO/'.server_files/AAEmu.Game/Data/compact.sqlite3'
    with sqlite3.connect(compact.as_uri()+'?mode=ro', uri=True) as db:
        valid_ids = {row[0] for row in db.execute('SELECT id FROM doodad_almighties')}
    result = {label: verify(base/'AAEmu.Game/Data/Worlds/main_world', valid_ids) for label, base in
              [('source', REPO), ('runtime', REPO/'.server_files')]}
    audit = read_json(AUDIT/'audit.json')
    build = read_json(OUT/'placement-build.json')
    repaired = set(build['regional_quests'])
    with (OUT/'quest-repair-status.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(('quest_id', 'title_es', 'repair', 'acceptance'))
        for quest in audit['quests']:
            fixes = []
            if quest['id'] in repaired:
                fixes.append('native_regional_placements')
            if quest['id'] in (1402, 1474, 2071):
                fixes.append('npc_spawn_consumer')
            if quest['id'] in (4294, 4295):
                fixes.append('placement_source_transaction')
            if fixes:
                writer.writerow((quest['id'], quest.get('title_es'), '+'.join(fixes), 'pending_retail_client'))
    (OUT/'catalog-verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
