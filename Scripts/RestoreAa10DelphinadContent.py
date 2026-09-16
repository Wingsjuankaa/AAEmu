"""Build Delphinad's server doodad catalog from immutable r575 cell exports.

Use --game-pak (read-only, requires cryptography) or --world-dir with extracted
game/worlds/instance_phantom_of_delphinad. Writes only --output when --apply is
given; only upgrades the pinned first catalog, backing it up before replacement.
Refuses other differing content. Coordinates/rotations use the same
cell parser as the validated Halcyona reconstruction. No DB or game_pak writes.
"""
import argparse
import hashlib
import json
import sqlite3
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reconstruccion_cliente_10/scripts'))
from build_halcyona_doodad_overlay import BLOCK_PATTERN, clean, quaternion_to_degrees

WORLD = 'instance_phantom_of_delphinad'
LEGACY_SHA256 = '1e065fa4a924717d639d17231391616355ea146c5240c5f077fe1cbd7b52b44c'
CELLS = {
    '001_001': 'b5a97696a14d7140cc1e28be190ef26e81944c2898ecf8683e2500b6b6623829',
    '001_002': '003d1c07f72a92bc294b532ad60f1326cf26678b8f064a98bbd52c27b0ef9a56',
}


def read_cells(args):
    if args.world_dir:
        return {cell: (args.world_dir / f'level_design/cells/{cell}/doodad.g').read_bytes()
                for cell in CELLS}
    from Aa10PakAppend import read_tail, aes, RECORD
    wanted = {f'game/worlds/{WORLD}/level_design/cells/{c}/doodad.g'.encode('ascii'): c for c in CELLS}
    result = {}
    with args.game_pak.open('rb') as stream:
        start, tail, count, _ = read_tail(stream)
        for i in range(count):
            record = aes(tail[i * RECORD:(i + 1) * RECORD])
            name = record[:264].split(b'\0', 1)[0]
            if name not in wanted:
                continue
            offset, size, duplicate, padding = struct.unpack_from('<qqqi', record, 264)
            if min(offset, size, padding) < 0 or size != duplicate or offset + size + padding > start:
                raise ValueError('Invalid native entry bounds')
            stream.seek(offset)
            payload = stream.read(size)
            if hashlib.md5(payload).digest() != record[292:308]:
                raise ValueError('Native entry MD5 mismatch')
            if wanted[name] in result:
                raise ValueError('Duplicate native entry')
            result[wanted[name]] = payload
    return result


def build(cells, database):
    rows = []
    for cell, digest in CELLS.items():
        payload = cells[cell]
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f'Unexpected r575 cell hash: {cell}')
        text = payload.decode('utf-8')
        matches = list(BLOCK_PATTERN.finditer(text))
        if sum(line.strip() == 'doodad' for line in text.splitlines()) != len(matches):
            raise ValueError(f'Unparsed native doodad: {cell}')
        cx, cy = map(int, cell.split('_'))
        for m in matches:
            roll, pitch, yaw = quaternion_to_degrees(*(float(m[k]) for k in ('qx', 'qy', 'qz', 'qw')))
            rows.append(dict(Id=0, UnitId=int(m['unit_id']), Title='', Position=dict(
                X=clean(cx * 1024 + float(m['x'])), Y=clean(cy * 1024 + float(m['y'])),
                Z=clean(float(m['z'])), Roll=roll, Pitch=pitch, Yaw=yaw),
                FuncGroupId=0, Scale=float(m['scale'])))
    if len(rows) != 68:
        raise ValueError('Expected 68 native placements')
    keys = [(r['UnitId'], *r['Position'].values()) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate native placement')
    hayden = [r for r in rows if r['UnitId'] == 15086]
    if len(hayden) != 1 or any(abs(hayden[0]['Position'][k] - v) > .001
                             for k, v in dict(X=1572.845, Y=2068.8956, Z=282.8).items()):
        raise ValueError('Hayden entry landmark mismatch')
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        for unit_id in sorted({r['UnitId'] for r in rows}):
            template = db.execute('select id from doodad_almighties where id=?', (unit_id,)).fetchone()
            phases = db.execute('select id from doodad_func_groups where doodad_almighty_id=? '
                                'and doodad_func_group_kind_id=1', (unit_id,)).fetchall()
            if not template or len(phases) != 1:
                raise ValueError(f'Missing/ambiguous template start phase: {unit_id}')
            # Zero delegates to the server's generic NPC-model fallback, which can
            # select a later Normal phase (Hayden 44632) instead of native Start.
            for row in rows:
                if row['UnitId'] == unit_id:
                    row['FuncGroupId'] = phases[0][0]
    return (json.dumps(rows, indent=2) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--game-pak', type=Path)
    source.add_argument('--world-dir', type=Path)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, nargs='+', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    payload = build(read_cells(args), args.database)
    plans = [(path, path.read_bytes() if path.exists() else None) for path in args.output]
    for path, before in plans:
        if before is not None and before != payload and hashlib.sha256(before).hexdigest() != LEGACY_SHA256:
            raise ValueError(f'Refusing to overwrite different catalog: {path}')
    for path, before in plans:
        changed = before != payload
        if args.apply and changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            if before is not None:
                if path.read_bytes() != before:
                    raise ValueError(f'Catalog changed during build: {path}')
                backup = path.with_name(path.name + '.before-native-phases')
                if backup.exists() and backup.read_bytes() != before:
                    raise ValueError(f'Backup differs: {backup}')
                if not backup.exists():
                    backup.write_bytes(before)
                path.write_bytes(payload)
            else:
                with path.open('xb') as stream:
                    stream.write(payload)
        print(json.dumps(dict(output=str(path), changed=changed, applied=args.apply,
                              count=68, sha256=hashlib.sha256(payload).hexdigest())))


if __name__ == '__main__':
    main()
