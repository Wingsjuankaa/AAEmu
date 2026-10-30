"""Closed scene identities for the private AA10 development runtime."""
from pathlib import Path
import json

HALL = {'zoneKey': 379, 'zoneName': 'gatekeeper_hall', 'worldId': 0,
        'origin': {'X': 500.295, 'Y': 38373.5, 'Z': 129.948, 'Rotation': 0.0}}
LAB = {'zoneKey': 411, 'zoneName': 'aa10_sandbox_lab', 'worldId': 0,
       'origin': {'X': 575.0, 'Y': 506.0, 'Z': 256.25, 'Rotation': 0.0}}


def definition(zone_key):
    if zone_key == HALL['zoneKey']:
        return HALL
    if zone_key == LAB['zoneKey']:
        return LAB
    raise ValueError('Only the accepted Hall or the separately installed Zone411 sandbox are supported')


def selected(root):
    path = Path(root)/'sandbox.json'
    value = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else HALL
    result = definition(value.get('zoneKey', 379))
    if value.get('zoneName', result['zoneName']) != result['zoneName']:
        raise ValueError('Sandbox Zone name and key disagree')
    return result


def verify_installation(root):
    root = Path(root).resolve()
    scene = selected(root)
    if scene['zoneKey'] == 379:
        return
    marker = json.loads((root/'zone411-installed.json').read_text(encoding='utf-8-sig'))
    if (marker.get('patch_id') != 'aa10-sandbox-zone411-v1' or marker.get('zoneKey') != 411 or
            marker.get('zoneName') != LAB['zoneName'] or marker.get('worldId') != 0 or
            marker.get('state') not in ('resources_verified', 'accepted')):
        raise ValueError('Zone411 resources have not passed the isolated installation checks')
    for role, relative in [('client', 'client/game_pak'), ('native', 'zone/game_pak')]:
        package = (root/relative).resolve()
        record = marker['packages'][role]
        stat = package.stat()
        if (Path(record['path']).resolve() != package or stat.st_size != record['size'] or
                stat.st_mtime_ns != record['mtime_ns'] or stat.st_ino != record['inode']):
            raise ValueError('A Zone411 package differs from its verified physical identity')
