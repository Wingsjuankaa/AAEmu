"""Build a pinned retail-terrain scene offline; never opens or modifies a game package/runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import xml.etree.ElementTree as ET

PROJECT = Path('E:/AAEmu/rama_10')
ARTIFACTS = PROJECT/'artifacts/sandbox'
EVIDENCE = PROJECT/'forensics/output/aa10-client-forensics/sandbox-zone-separate-20261029/assets'
DEFAULT_SOURCE = EVIDENCE/'donor-ga/worlds/instance_training_camp_1on1_ga'
DEFAULT_SOURCE_MANIFEST = EVIDENCE/'donor-analysis.json'
SOURCE_MANIFEST_SHA256 = '2ec711899b8f637c02dcb812986b80145ff3cde1eeaeb556b5679ee72e22946b'
SOURCE_FILE_COUNT = 413
SOURCE_WORLD = 'instance_training_camp_1on1_GA'
PATCH_ID = 'aa10-sandbox-zone-411-assets-v1'
MANIFEST_NAME = 'sandbox-zone-assets.manifest.json'
PACKAGE_PREFIX = 'game/worlds/main_world/'

# These are placements, not geometry. The source has no npc_spawners.g to empty or synthesize.
OMITTED = {
    'level_design/cells/000_000/doodad.g':
        'Two authored interactive arena iron gates, doodad9472, are outside the owned sandbox actor/reset profile.',
    'level_design/zone/406/editor/spawn_point.xml':
        'Donor faction/instant_corps entry metadata; the fixed sandbox origin is recorded separately.',
    'level_design/zone/406/world_server/spawn_point.g':
        'Donor faction spawn and two elevated instant_corps points; do not inherit PvP respawn placements.',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ('.', '..') or ':' in part for part in path.parts) or '\\' in value:
        raise ValueError('Unsafe source-relative asset path')
    return path


def physical_tree_files(directory):
    if directory.is_symlink() or directory.is_junction():
        raise ValueError('Asset trees must be physical directories')
    result = {}
    for path in directory.rglob('*'):
        if path.is_symlink() or path.is_junction():
            raise ValueError('Asset trees cannot contain links or junctions')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = path
    return result


def validate_source(source, source_manifest):
    source, source_manifest = Path(source).absolute(), Path(source_manifest).absolute()
    if source.resolve().drive.upper() != 'E:' or source_manifest.resolve().drive.upper() != 'E:':
        raise ValueError('The donor and evidence must stay on E')
    encoded = source_manifest.read_bytes()
    if sha256(encoded) != SOURCE_MANIFEST_SHA256:
        raise ValueError('The pinned donor evidence manifest changed')
    manifest = json.loads(encoded)
    if manifest.get('kind') != 'read-only-static-donor-analysis' or manifest.get('world', {}).get('name') != SOURCE_WORLD:
        raise ValueError('Wrong retail donor identity')
    records = manifest.get('manifest', [])
    if len(records) != SOURCE_FILE_COUNT:
        raise ValueError('The donor manifest has an unexpected file count')
    files = physical_tree_files(source)
    names = [safe_relative(record['relative']).as_posix() for record in records]
    if len(set(names)) != len(names) or set(files) != set(names):
        raise ValueError('The complete donor file tree changed')
    payloads = {}
    for record in records:
        data = files[record['relative']].read_bytes()
        if len(data) != record['size'] or sha256(data) != record['sha256'].lower():
            raise ValueError(f"Donor payload drift: {record['relative']}")
        payloads[record['relative']] = data
    if not set(OMITTED).issubset(payloads):
        raise ValueError('The expected authored-placement files are missing')
    return payloads


def replace_attribute(data, element, attribute, old, new):
    pattern = rb'(<'+element.encode()+rb'\b[^>]*\b'+attribute.encode()+rb'=")'+re.escape(old.encode())+rb'(")'
    result, count = re.subn(pattern, lambda match: match[1]+new.encode()+match[2], data)
    if count != 1:
        raise ValueError(f'Expected one exact {element}.{attribute}={old} identity')
    return result


def rewrite_world_xml(data):
    root = ET.fromstring(data)
    expected = {'name': SOURCE_WORLD, 'resolution':'1024', 'unitSize':'2', 'cellXCount':'2',
                'cellYCount':'2', 'isInstance':'1', 'oceanLevel':'100', 'maxTerrainHeight':'4096'}
    zones = root.findall('./ZoneList/Zone')
    if root.tag != 'World' or any(root.get(key) != value for key, value in expected.items()) or len(zones) != 1:
        raise ValueError('The donor world dimensions, scale or zone list changed')
    zone = zones[0]
    cells = zone.findall('./cellList/cell')
    sectors = {(int(sector.get('x')),int(sector.get('y'))) for sector in zone.findall('.//sector')}
    if (zone.attrib != {'name':SOURCE_WORLD,'id':'406','originX':'0','originY':'0'} or
            len(cells) != 1 or cells[0].attrib != {'x':'0','y':'0'} or
            len(zone.findall('.//sector')) != 256 or sectors != {(x,y) for x in range(16) for y in range(16)}):
        raise ValueError('The donor is no longer the single complete cell000_000')
    data = replace_attribute(data, 'World', 'name', SOURCE_WORLD, 'main_world')
    data = replace_attribute(data, 'World', 'isInstance', '1', '0')
    data = replace_attribute(data, 'Zone', 'name', SOURCE_WORLD, 'aa10_sandbox_lab')
    return replace_attribute(data, 'Zone', 'id', '406', '411')


def rewrite_world_g(data):
    original = data.decode('utf-8')
    required = {f'name {SOURCE_WORLD}':2, 'id 406':1, 'zones 406':1,
                'cellX 2':1, 'cellY 2':1, 'oceanLevel 100':1}
    if any(original.count(text) != count for text,count in required.items()):
        raise ValueError('The native world.g identity/layout changed')
    # The root and partition names have distinct consumers.
    result = original.replace(f'name {SOURCE_WORLD}', 'name main_world', 1)
    result = result.replace(f'name {SOURCE_WORLD}', 'name aa10_sandbox_lab', 1)
    return result.replace('id 406', 'id 411').replace('zones 406', 'zones 411').encode('utf-8')


def rewrite_leveldata(data):
    root = ET.fromstring(data)
    info = root.find('LevelInfo')
    expected = {'Name':'406','HeightmapSize':'4096','HeightmapUnitSize':'2',
                'HeightmapMaxHeight':'4096','WaterLevel':'100','TerrainSectorSizeInMeters':'64'}
    if root.tag != 'LevelData' or info is None or any(info.get(key) != value for key,value in expected.items()):
        raise ValueError('A donor LevelData identity or terrain scale changed')
    return replace_attribute(data, 'LevelInfo', 'Name', '406', '411')


def destination_name(relative):
    if relative.startswith('zone/406/'):
        return 'zone/411/'+relative[len('zone/406/'):]
    if relative.startswith('level_design/zone/406/'):
        return 'level_design/zone/411/'+relative[len('level_design/zone/406/'):]
    if relative == 'zone/instance_training_camp_1on1_ga_user.xml':
        return 'zone/aa10_sandbox_lab_user.xml'
    return relative


def plan(payloads):
    files, records, omitted = {}, [], []
    for relative, source_data in sorted(payloads.items()):
        if relative in OMITTED:
            omitted.append({'source':relative,'sourceBytes':len(source_data),'sourceSha256':sha256(source_data),
                            'reason':OMITTED[relative]})
            continue
        data, operation = source_data, 'byte-exact-copy'
        if relative == 'world.xml':
            data, operation = rewrite_world_xml(data), 'world-identity-and-non-instance'
        elif relative == 'world.g':
            data, operation = rewrite_world_g(data), 'native-world-and-partition-identity'
        elif relative in ('cells/000_000/client/leveldata.xml','zone/406/leveldata.xml'):
            data, operation = rewrite_leveldata(data), 'levelinfo-name-only'
        entry = PACKAGE_PREFIX+destination_name(relative)
        if entry in files:
            raise ValueError('Two donor files resolve to the same output entry')
        files[entry] = data
        records.append({'source':relative,'sourceBytes':len(source_data),'sourceSha256':sha256(source_data),
                        'entry':entry,'bytes':len(data),'sha256':sha256(data),'operation':operation})
    required = ('world.xml','world.g','surface.xml','vegetation.xml','env.xml',
                'cells/000_000/client/terrain/heightmap.dat','cells/000_000/client/terrain/cover.ctc',
                'cells/000_000/client/brush.dat','cells/000_000/client/object.dat',
                'cells/000_000/client/statobjs.dat','zone/411/leveldata.xml')
    if any(PACKAGE_PREFIX+name not in files for name in required):
        raise ValueError('The new scene lacks a required terrain/geometry/zone payload')
    manifest = {'schema':1,'patchId':PATCH_ID,'sourceManifestSha256':SOURCE_MANIFEST_SHA256,
        'sourceWorld':SOURCE_WORLD,'sourceFiles':len(payloads),'sourceBytes':sum(map(len,payloads.values())),
        'destination':{'worldName':'main_world','worldId':0,'zoneKey':411,'zoneName':'aa10_sandbox_lab',
                       'cellXCount':2,'cellYCount':2,'isInstance':False,
                       'origin':{'X':575,'Y':506,'Z':260,'Rotation':0}},
        'scope':'Only the private sandbox main_world metadata; activation requires package/DB/config rollback of the previous scene.',
        'sharedGeometry':'Cell binary payloads are copied byte-for-byte; global surface and vegetation stay coherent with their donor world.',
        'npcSpawners':'No npc_spawners.g exists in the pinned donor; no empty binary/text format is fabricated.',
        'files':records,'omitted':omitted,'outputFiles':len(files),'outputBytes':sum(map(len,files.values()))}
    return files, manifest


def validate_output(output, source):
    requested = Path(output).absolute()
    resolved, allowed = requested.resolve(), ARTIFACTS.resolve()
    if resolved.drive.upper() != 'E:' or resolved == allowed or not resolved.is_relative_to(allowed):
        raise ValueError('New output must be a child of E:/AAEmu/rama_10/artifacts/sandbox')
    if resolved == source.resolve() or resolved.is_relative_to(source.resolve()) or source.resolve().is_relative_to(resolved):
        raise ValueError('Output and immutable donor cannot overlap')
    for path in [requested, *requested.parents]:
        if path.exists() and (path.is_symlink() or path.is_junction()):
            raise ValueError('The output path cannot traverse links or junctions')
    return resolved


def build(source=DEFAULT_SOURCE, output=None, source_manifest=DEFAULT_SOURCE_MANIFEST):
    if output is None:
        raise ValueError('An explicit new output directory is required')
    source = Path(source)
    output = validate_output(output, source)
    payloads = validate_source(source, source_manifest)
    files, manifest = plan(payloads)
    files[MANIFEST_NAME] = json_bytes(manifest)
    if output.exists():
        actual = physical_tree_files(output)
        if set(actual) != set(files) or any(actual[name].read_bytes() != data for name,data in files.items()):
            raise ValueError('Existing output is not the exact complete build; refusing to overwrite it')
        return manifest, 'already-built'
    output.parent.mkdir(parents=True,exist_ok=True)
    # A final directory only appears after every byte has been written and re-read on the same E volume.
    with tempfile.TemporaryDirectory(prefix=f'.{output.name}.building-',dir=output.parent) as temporary:
        stage = Path(temporary)
        for name,data in files.items():
            path = stage/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            if path.read_bytes() != data:
                raise OSError(f'Output verification failed: {name}')
        stage.rename(output)
    return manifest, 'built'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=DEFAULT_SOURCE)
    parser.add_argument('--source-manifest',type=Path,default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    manifest, state = build(args.source,args.output,args.source_manifest)
    print(json.dumps({'state':state,'patchId':PATCH_ID,'output':str(args.output.resolve()),
                      'files':manifest['outputFiles'],'bytes':manifest['outputBytes'],
                      'omitted':len(manifest['omitted']),'manifestSha256':sha256(json_bytes(manifest))}))


if __name__ == '__main__':
    main()
