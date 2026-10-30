"""Derive the accepted V3 retail entry driver for the dedicated Zone411 scene."""
from pathlib import Path
import argparse
import hashlib
import json

import PatchAa10SandboxAutoEntry as accepted

ENTRY = 'game/scriptsbin64/x2ui/loginstage_new/connect/stage_server.alb'
NAME = 'loginstage_new/connect/stage_server'
ZONE_KEY = 411
SOURCE = Path('E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-intake-20261029/autoentry/effective/scripts/x2ui/loginstage_new/connect/stage_server.lua')
LUAC = Path('E:/AAEmu-Research/work/lua-5.1.5-msvc/lua-5.1.5/src/luac51.exe')


def source_for_zone(source):
    baseline = accepted.effective_source(NAME, source)
    patched = accepted.patch_source(NAME, baseline)
    patched = accepted.once(patched, '"world":1,"zone":379', '"world":1,"zone":411')
    return accepted.once(patched, 'then zoneId = 379 end', 'then zoneId = 411 end')


def build(output, source=SOURCE, luac=LUAC):
    output = Path(output).resolve()
    if output.drive.upper() != 'E:' or output.exists():
        raise ValueError('The entry output must be a new file on E')
    contracts = json.loads(accepted.CONTRACTS.read_text(encoding='utf-8'))
    contract = next(entry for entry in contracts['entries'] if entry['name'] == NAME)
    accepted.lua.v1.require_exact(source, contract['source_sha256'])
    accepted.lua.v1.require_exact(luac, contracts['luac_sha256'])
    text = source.read_text(encoding='utf-8-sig')
    previous = accepted.compile_source(accepted.patch_source(NAME, accepted.effective_source(NAME, text)), luac)
    previous += bytes(contract['size'] - len(previous))
    if hashlib.sha256(previous).hexdigest().upper() != contract['patched_sha256']:
        raise ValueError('The source/compiler do not reproduce the accepted V3 consumer')
    payload = accepted.compile_source(source_for_zone(text), luac)
    if len(payload) > contract['size']:
        raise ValueError('The derived driver exceeds its accepted entry capacity')
    payload += bytes(contract['size'] - len(payload))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return {'entry': ENTRY, 'zone_key': ZONE_KEY, 'size': len(payload),
            'before_sha256': contract['patched_sha256'],
            'after_sha256': hashlib.sha256(payload).hexdigest().upper(), 'payload_path': str(output),
            'source_sha256': contract['source_sha256'], 'luac_sha256': contracts['luac_sha256'],
            'driver': 'accepted V3 native world/character handlers; fixed Zone411'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
