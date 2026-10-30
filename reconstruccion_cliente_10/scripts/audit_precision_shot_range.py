"""Read-only r575 geometry frontier for skill23592; never edits deployed data."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import struct

ROOT = Path('E:/AAEmu/rama_10')
SOURCES = {
    'authoritative': ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3',
    'spanish_client': ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/game/db/compact.sqlite3',
    'sandbox_client': ROOT/'runtime/sandbox-aa10/client/game/db/compact.sqlite3',
    'sandbox_server': ROOT/'runtime/sandbox-aa10/zone411/server/compact.sqlite3',
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()


def build(output):
    output = Path(output).resolve()
    if output.drive.upper() != 'E:' or output.exists():
        raise ValueError('A new output directory on E is required')
    output.mkdir(parents=True)
    target = sqlite3.connect(output/'geometry.sqlite3')
    target.executescript('''
      CREATE TABLE artifacts(name TEXT PRIMARY KEY,path TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL);
      CREATE TABLE rows(source TEXT NOT NULL,tbl TEXT NOT NULL,id INTEGER NOT NULL,data TEXT NOT NULL,PRIMARY KEY(source,tbl,id));
      CREATE TABLE checks(source TEXT NOT NULL,name TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(source,name));
    ''')
    selections = {
        'skills': 'SELECT * FROM skills WHERE plot_id=1226 ORDER BY id',
        'plots': 'SELECT * FROM plots WHERE id=1226 ORDER BY id',
        'plot_events': 'SELECT * FROM plot_events WHERE plot_id=1226 ORDER BY id',
        'plot_next_events': 'SELECT * FROM plot_next_events WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=1226) ORDER BY id',
        'plot_event_conditions': 'SELECT * FROM plot_event_conditions WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=1226) ORDER BY id',
        'plot_conditions': 'SELECT * FROM plot_conditions WHERE id IN (SELECT condition_id FROM plot_event_conditions WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=1226)) ORDER BY id',
        'plot_effects': 'SELECT * FROM plot_effects WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=1226) ORDER BY id',
        'aoe_shapes': 'SELECT * FROM aoe_shapes WHERE id IN (4841,4842,4843,5037) ORDER BY id',
        'enum_aoe_shape_kinds': 'SELECT * FROM enum_aoe_shape_kinds ORDER BY id',
        'enum_plot_area_target_kinds': 'SELECT * FROM enum_plot_area_target_kinds ORDER BY id',
    }
    for name, path in SOURCES.items():
        target.execute('INSERT INTO artifacts VALUES(?,?,?,?)', (name,str(path),digest(path),path.stat().st_size))
        source = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
        source.row_factory = sqlite3.Row
        for check in ('quick_check', 'integrity_check'):
            result = source.execute('PRAGMA '+check).fetchall()
            if [row[0] for row in result] != ['ok']: raise ValueError((name, check, result))
            target.execute('INSERT INTO checks VALUES(?,?,?)', (name,check,'ok'))
        for table, query in selections.items():
            if source.execute('SELECT count(*) FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0] == 0:
                if not table.startswith('enum_'): raise ValueError('Required geometry table missing: '+table)
                target.execute('INSERT INTO checks VALUES(?,?,?)', (name,'table:'+table,'absent from compact projection; authoritative enum retained'))
                continue
            for row in source.execute(query):
                target.execute('INSERT INTO rows VALUES(?,?,?,?)',
                    (name,table,row['id'],json.dumps(dict(row),ensure_ascii=False,sort_keys=True,separators=(',',':'))))
        source.close()
    # Reanchor the existing native line-OBB consumer against the actual dedicated DLL.
    binary = ROOT/'runtime/sandbox-aa10/zone/Bin64/x2game-dev_dedicate.dll'
    data = binary.read_bytes()
    pe = struct.unpack_from('<I', data, 60)[0]
    count = struct.unpack_from('<H', data, pe+6)[0]
    optional = struct.unpack_from('<H', data, pe+20)[0]
    sections = [struct.unpack_from('<4I', data, pe+24+optional+40*i+8) for i in range(count)]
    evidence = ROOT/'forensics/output/aa10-client-forensics/archery-mist-repair-20260911/zone-core/397b7e60.bytes'
    ranges = []
    for line in evidence.read_text().splitlines():
        rva, hexbytes = line.split()
        rva, expected = int(rva), bytes.fromhex(hexbytes)
        section = next(s for s in sections if s[1] <= rva < s[1]+max(s[0],s[2]))
        offset = section[3]+rva-section[1]
        if data[offset:offset+len(expected)] != expected: raise ValueError('Native line consumer drift')
        ranges.append({'rva':hex(rva),'bytes':len(expected),'sha256':hashlib.sha256(expected).hexdigest()})
    target.execute('INSERT INTO artifacts VALUES(?,?,?,?)', ('native_zone',str(binary),digest(binary),len(data)))
    target.commit()
    assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    total = target.execute('SELECT count(*) FROM rows').fetchone()[0]
    target.close()
    manifest = {'schema':1,'scope':'skill23592/plot1226 geometry; not full combat reconstruction',
                'rows':total,'geometry_sha256':digest(output/'geometry.sqlite3'),
                'native':{'sha256':digest(binary),'architecture':'x64','image_base':'0x39000000',
                          'line_obb_consumer':'0x7b7e60','ranges':ranges},
                'positive':['all four sources agree on skill23592 max_range45 and line4843 values3/25/3',
                            'native line OBB uses symmetric min/max values and half-extents, not a25m full length'],
                'limits':['native debug OBB corroborates descriptor geometry; no claim of complete native server target selection',
                          'calc_distance/adjust_angle semantics outside this fixed-length repair',
                          'AA8 ForwardCuboid and upstream fixed-length code are comparators, not native authority']}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'rows':total,'sha256':manifest['geometry_sha256']}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    build(p.parse_args().output)
