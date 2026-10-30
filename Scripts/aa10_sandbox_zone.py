"""Stage and install the separate Zone411 scene in the private sandbox only."""
from __future__ import annotations
import argparse
import calendar
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

import aa10_sandbox as sandbox
import aa10_sandbox_scenarios as scenes
import Aa10SandboxZonePak as packages
import ApplyAa10SandboxAutoEntry as entry_install
import BuildAa10SandboxZoneEntry as entry_builder

ROOT = sandbox.DEFAULT_ROOT
WORK = sandbox.PROJECT/'forensics/output/aa10-client-forensics/sandbox-zone-separate-20261029'
ASSETS = sandbox.PROJECT/'artifacts/sandbox/zone411-assets-a'
CATALOGS = sandbox.PROJECT/'artifacts/sandbox-zone411/catalog-builder'
ASSET_MANIFEST_SHA = '27D44CD598365785C6AAA8644AA1D5C145828B25AF31395ECC42604AED168EBA'
CATALOG_SHA = {'full': 'FD66192AE065F42B92579718B6FB91A51A52947D2E0FBFF29D89ADC8DA7E4304',
               'compact': '59C47834B802737890304F8584347E85DD61DC519AD62230C66F0760BDA33FCA'}
BATCH = sandbox.REPO/'reconstruccion_cliente_10/tools/PakBatchExtract/bin/Release/net10.0/PakBatchExtract.dll'
SENTINELS = ['game/ui/icon/achievement/icon_achieve_0001.dds',
             'game/ui/map/map_resources/arche_mall/en_us/world.dds',
             'game/scriptsbin64/x2ui/crafting/crafting_view.alb',
             'game/scriptsbin64/x2ui/loginstage_new/character_select/character_select.alb']
PATCH_ID = 'aa10-sandbox-zone411-v1'


def digest(path):
    return sandbox.sha256(path).upper()


def lobby_configuration(document):
    """The proxy lobby must load a level that exists in the reduced private world."""
    from copy import deepcopy
    result = deepcopy(document)
    lobby = result['InitialConfig']
    if lobby.get('LobbyLevel') not in ('w_hanuimaru_1', scenes.LAB['zoneName']):
        raise ValueError('Unexpected sandbox lobby level; refusing an unrelated override')
    lobby['LobbyLevel'] = scenes.LAB['zoneName']
    return result


def ensure_hash(path, expected):
    if digest(path) != expected.upper():
        raise ValueError('Pinned resource drift: '+str(path))


def stats(path):
    path = Path(path).resolve()
    stat = path.stat()
    return {'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'inode': stat.st_ino}


def epoch_ns(value):
    whole, fraction = value.rstrip('Z').split('.')
    return calendar.timegm(datetime.strptime(whole, '%Y-%m-%dT%H:%M:%S').timetuple())*10**9+int((fraction+'000000000')[:9])


def run(*arguments):
    return sandbox.run(arguments, root=ROOT).stdout.decode('utf-8', errors='replace')


def extract(package, names, directory):
    directory.mkdir(parents=True, exist_ok=True)
    listing = directory/'requested-entries.txt'
    listing.write_text('\n'.join(sorted(set(names)))+'\n', encoding='utf-8')
    log = run('dotnet', BATCH, package, listing, directory)
    (directory/'extraction.log').write_text(log, encoding='utf-8')
    return {name: {'path': str(directory/name.removeprefix('game/')),
                   'size': (directory/name.removeprefix('game/')).stat().st_size,
                   'sha256': digest(directory/name.removeprefix('game/'))} for name in names}


def source_index(role):
    import csv
    name = 'effective-client-index.tsv' if role == 'client' else 'effective-native-index.tsv'
    with (WORK/name).open(encoding='utf-8') as source:
        return {row['name'] for row in csv.DictReader(source, delimiter='\t')}


def prepare(output):
    output = Path(output).absolute().resolve()
    if (not output.is_relative_to(sandbox.PROJECT/'artifacts/sandbox') or output.exists() or
            output.drive.upper() != 'E:'):
        raise ValueError('Use a NEW staging directory under artifacts/sandbox on E')
    sandbox.verify_runtime_binding(ROOT)
    if scenes.selected(ROOT)['zoneKey'] != 379:
        raise ValueError('Preparation starts from the accepted Hall scene only')
    ensure_hash(ASSETS/'sandbox-zone-assets.manifest.json', ASSET_MANIFEST_SHA)
    assets = sandbox.read_jsonc(ASSETS/'sandbox-zone-assets.manifest.json')
    catalogs = {role: CATALOGS/f'{role}-a.sqlite3' for role in CATALOG_SHA}
    for role, path in catalogs.items(): ensure_hash(path, CATALOG_SHA[role])
    client = ROOT/'client/game_pak'
    sandbox.validate_client(ROOT)
    client_sha = entry_install.verified_before_hash(client, ROOT/'autoentry-applied.json')
    native = ROOT/'zone/game_pak'
    native_identity = sandbox.read_jsonc(WORK/'native-package-identity.json')
    if (native.stat().st_size != native_identity['bytes'] or
            native.stat().st_mtime_ns != epoch_ns(native_identity['lastWriteUtc']) or
            Path(native_identity['path']).resolve() != native.resolve()):
        raise ValueError('The read-only full native package hash is no longer bound to this file')
    output.mkdir(parents=True)
    driver = entry_builder.build(output/'entry/stage_server.alb')
    files = []
    for record in assets['files']:
        payload = ASSETS/record['entry']
        ensure_hash(payload, record['sha256'])
        files.append({'entry': record['entry'], 'payload_path': str(payload), 'after_sha256': record['sha256'].upper()})
    plans = {}
    for role, package, package_sha, catalog in [
            ('client', client, client_sha, catalogs['compact']),
            ('native', native, native_identity['sha256'], catalogs['full'])]:
        records = [dict(record) for record in files]
        records.append({'entry': 'game/db/compact.sqlite3', 'payload_path': str(catalog), 'after_sha256': digest(catalog)})
        if role == 'client': records.append({key: driver[key] for key in ('entry', 'payload_path', 'after_sha256')})
        present = source_index(role)
        before = extract(package, [record['entry'] for record in records if record['entry'] in present]+SENTINELS,
                         output/f'before-{role}')
        for record in records:
            old = before.get(record['entry'])
            record.update(before_sha256=old['sha256'] if old else None, before_size=old['size'] if old else None)
        if role == 'client' and next(record for record in records if record['entry'] == driver['entry'])['before_sha256'] != driver['before_sha256']:
            raise ValueError('The actual client entry driver differs from the accepted V3 input')
        contract = {'schema': 1, 'patch_id': PATCH_ID, 'package': dict(stats(package), sha256=package_sha), 'entries': records}
        sandbox.write_json(output/f'{role}-contract.json', contract)
        print(f'Preparando un solo commit de recursos para {role}...', flush=True)
        prepared = packages.prepare(package, contract, output/f'{role}-plan')
        plans[role] = {'manifest': str(output/f'{role}-plan/manifest.json'),
                       'sha256': digest(output/f'{role}-plan/manifest.json'),
                       'sentinels': {name: before[name]['sha256'] for name in SENTINELS}}
    spawns_path = sandbox.REPO/'.server_files/AAEmu.Game/Data/Worlds/world_spawns.json'
    spawns = sandbox.read_jsonc(spawns_path)
    spawns = [spawn for spawn in spawns if spawn.get('Name') != 'main_world']
    spawns.append({'Name': 'main_world', 'SpawnPosition': {'ZoneId': 411,
                   **{axis: scenes.LAB['origin'][axis] for axis in ('X', 'Y', 'Z')}, 'Yaw': 0}})
    sandbox.write_json(output/'server/world_spawns.json', spawns)
    actions = []
    for branch in ('client', 'zone'):
        for record in files:
            actions.append({'target': str(ROOT/branch/record['entry']), 'source': record['payload_path'], 'sha256': record['after_sha256']})
        # Asset names already include game/, so targets are client/game/... and zone/game/....
        for filename, profile in [('compact.sqlite3', 'compact' if branch == 'client' else 'full'), ('game.sqlite3', 'full')]:
            actions.append({'target': str(ROOT/branch/'game/db'/filename), 'source': str(catalogs[profile]), 'sha256': CATALOG_SHA[profile]})
    actions += [{'target': str(ROOT/'zone411/server/compact.sqlite3'), 'source': str(catalogs['full']), 'sha256': CATALOG_SHA['full']},
                {'target': str(ROOT/'zone411/server/world_spawns.json'), 'source': str(output/'server/world_spawns.json'),
                 'sha256': digest(output/'server/world_spawns.json')}]
    plan = {'schema': 1, 'patch_id': PATCH_ID, 'state': 'prepared', 'root': str(ROOT), 'zoneKey': 411,
            'zoneName': scenes.LAB['zoneName'], 'worldId': 0, 'origin': scenes.LAB['origin'],
            'assets_manifest_sha256': ASSET_MANIFEST_SHA, 'packages': plans, 'file_actions': actions,
            'driver': driver, 'native_db_location': str(ROOT/'zone/game/db/compact.sqlite3'),
            'opaque_packed_game_sqlite3': 'unchanged: encrypted source payload; use the explicit plaintext native db_location',
            'lifecycle': 'not authorized by prepare; requires explicit Zone411 test authorization',
            'native_acceptance': 'pending'}
    sandbox.write_json(output/'deployment.json', plan)
    print(json.dumps({'state': 'prepared', 'plan': str(output/'deployment.json'), 'sha256': digest(output/'deployment.json')}))
    return plan


def actor_sql(sql):
    label = run('docker', 'inspect', 'aaemu10-sandbox-db-1', '--format',
                '{{index .Config.Labels "com.docker.compose.project"}}').strip()
    if label != sandbox.COMPOSE_PROJECT:
        raise ValueError('Refusing a character operation outside the private sandbox database')
    result = sandbox.run(['docker', 'exec', '-i', 'aaemu10-sandbox-db-1', 'sh', '-c',
                          'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names'],
                         root=ROOT, input_bytes=sql.encode('ascii'), check=False)
    if result.returncode:
        raise RuntimeError('The isolated character transaction failed; no database diagnostic was logged')
    return result.stdout.decode('utf-8').strip()


def actor_position():
    fields = ('id', 'account_id', 'name', 'zone_id', 'x', 'y', 'z', 'yaw', 'pitch', 'roll')
    expression = ','.join(f"'{name}',{name}" for name in fields)
    value = actor_sql(f'SELECT JSON_OBJECT({expression}) FROM aaemu_game.characters WHERE id=1001 AND account_id=1;')
    actor = json.loads(value)
    if actor.get('id') != 1001 or actor.get('account_id') != 1 or actor.get('name') != 'Sandbox':
        raise ValueError('The fixed sandbox character identity changed')
    return actor


def set_actor_position(value):
    import math
    names = ('zone_id', 'x', 'y', 'z', 'yaw', 'pitch', 'roll')
    if int(value['zone_id']) not in (379, 411) or any(not math.isfinite(float(value[name])) for name in names):
        raise ValueError('Invalid bounded sandbox character position')
    fields = ','.join(f'{name}={value[name]}' for name in names)
    text = actor_sql(f"START TRANSACTION; UPDATE aaemu_game.characters SET {fields} WHERE id=1001 AND account_id=1 AND name='Sandbox'; "
                     "SELECT COUNT(*) FROM aaemu_game.characters WHERE id=1001 AND account_id=1 AND name='Sandbox'; COMMIT;")
    if text.splitlines() != ['1']:
        raise RuntimeError('The private character transaction did not confirm exactly one actor')


def secure_backup():
    directory = ROOT/'secrets/zone411-backups'/sandbox.timestamp()
    directory.mkdir(parents=True, exist_ok=False)
    principal = os.environ.get('USERDOMAIN', '')+'\\'+os.environ['USERNAME']
    sandbox.run(['icacls', directory, '/inheritance:r', '/grant:r', principal+':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], root=ROOT)
    return directory


def owned_target(path):
    requested = Path(path).absolute()
    resolved = requested.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or requested.is_symlink() or requested.is_junction():
        raise ValueError('A deployment file escaped the private sandbox root')
    return resolved


def backup_files(paths, directory):
    records = []
    for value in sorted(set(map(str, paths))):
        path = owned_target(value)
        record = {'target': str(path), 'existed': path.exists()}
        if path.exists():
            saved = directory/'files'/path.relative_to(ROOT)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            record.update(backup=str(saved), sha256=digest(saved))
        records.append(record)
    sandbox.write_json(directory/'files.json', records)
    return records


def restore_files(records):
    for record in reversed(records):
        path = owned_target(record['target'])
        if record['existed']:
            ensure_hash(record['backup'], record['sha256'])
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record['backup'], path)
        elif path.exists():
            path.unlink()


def close_owned_client():
    target = str(ROOT/'client/Bin64/archeage.exe').replace("'", "''")
    script = (f"$target='{target}'; $owned=@(Get-CimInstance Win32_Process -Filter \"Name='archeage.exe'\" | Where-Object ExecutablePath -eq $target); "
              "foreach($p in $owned){$now=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.ProcessId); "
              "if($now -and $now.ExecutablePath -eq $target -and $now.CreationDate -eq $p.CreationDate){Stop-Process -Id $p.ProcessId -ErrorAction Stop}}")
    run('powershell.exe', '-NoProfile', '-Command', script)


def replace_compose_bindings(value):
    result = json.loads(json.dumps(value))
    volumes = result['services']['game']['volumes']
    client = [mount for mount in volumes if mount.get('target') == '/app/game/ClientData']
    data = [mount for mount in volumes if mount.get('target') == '/app/game/Data']
    if len(client) != 1 or len(data) != 1 or Path(data[0]['source']).resolve() != (sandbox.REPO/'.server_files/AAEmu.Game/Data').resolve():
        raise ValueError('Unexpected sandbox content/data mount; refusing to rebind it')
    client[0]['source'] = str(ROOT/'client').replace('\\', '/')
    shadows = {'/app/game/Data/compact.sqlite3': ROOT/'zone411/server/compact.sqlite3',
               '/app/game/Data/Worlds/world_spawns.json': ROOT/'zone411/server/world_spawns.json'}
    result['services']['game']['volumes'] = [mount for mount in volumes if mount.get('target') not in shadows]
    result['services']['game']['volumes'] += [{'type': 'bind', 'source': str(path).replace('\\', '/'),
                                            'target': target, 'read_only': True} for target, path in shadows.items()]
    return result


def load_plan(path, expected_sha):
    path = Path(path).resolve()
    if not path.is_relative_to(sandbox.PROJECT/'artifacts/sandbox'):
        raise ValueError('Use the reviewed staging plan on E')
    ensure_hash(path, expected_sha)
    plan = sandbox.read_jsonc(path)
    if (plan.get('schema'), plan.get('patch_id'), plan.get('root'), plan.get('zoneKey'), plan.get('zoneName')) != (
            1, PATCH_ID, str(ROOT), 411, scenes.LAB['zoneName']):
        raise ValueError('The deployment plan is not for the fixed private Zone411')
    for record in plan['file_actions']:
        owned_target(record['target']); ensure_hash(record['source'], record['sha256'])
    for record in plan['packages'].values():
        packages._load_manifest(record['manifest'], record['sha256'])
        if not record.get('expected_full_sha256') or not record.get('offline_entries_verified'):
            raise ValueError('The complete package rehearsal and deterministic final hash are required')
    for record in plan.get('tool_sources', []): ensure_hash(record['path'], record['sha256'])
    return plan


def prove(path):
    """Read-only full before/expected-after hashes and independent sparse extraction checks."""
    path = Path(path).resolve()
    plan = sandbox.read_jsonc(path)
    results = {}
    for role, record in plan['packages'].items():
        _, package, package_plan = packages._load_manifest(record['manifest'], record['sha256'])
        original = stats(package)
        expected = sandbox.read_jsonc(WORK/f'rehearsal/{role}411.fixture.expected.json')
        extracted = WORK/f'rehearsal/{role}-extracted'
        for name, value in expected.items():
            ensure_hash(extracted/name.removeprefix('game/'), value)
        before, after = hashlib.sha256(), hashlib.sha256()
        remaining = package_plan['suffix_offset']
        print(f'Calculando identidad completa original y resultado determinista de {role}...', flush=True)
        with package.open('rb') as source:
            while remaining:
                block = source.read(min(4*1024*1024, remaining))
                if not block: raise ValueError('Truncated package prefix')
                before.update(block); after.update(block); remaining -= len(block)
            while block := source.read(4*1024*1024): before.update(block)
        with Path(package_plan['suffix_after']['path']).open('rb') as suffix:
            while block := suffix.read(4*1024*1024): after.update(block)
        if before.hexdigest().upper() != package_plan['package_before']['sha256'] or original != stats(package):
            raise ValueError('The complete original package identity changed during rehearsal')
        # Prove all encrypted non-target records and tombstones are literal, not just readable.
        old = Path(package_plan['suffix_before']['path']).read_bytes()
        new_start = package_plan['new_fat_offset']-package_plan['suffix_offset']
        with Path(package_plan['suffix_after']['path']).open('rb') as suffix:
            suffix.seek(new_start); new = suffix.read()
        replaced = sorted(entry['record_index'] for entry in package_plan['entries'] if entry['operation'] == 'replace')
        previous = 0
        for index in replaced:
            end = index*336
            if memoryview(old)[previous:end] != memoryview(new)[previous:end]: raise ValueError('Unrelated encrypted records changed')
            previous = (index+1)*336
        live_end = package_plan['live_before']*336
        if memoryview(old)[previous:live_end] != memoryview(new)[previous:live_end]: raise ValueError('Unrelated tail records changed')
        old_extra = old[live_end:live_end+package_plan['extras_before']*336]
        new_extra_start = package_plan['live_after']*336
        if old_extra != new[new_extra_start:new_extra_start+len(old_extra)]: raise ValueError('Opaque tombstones changed')
        record.update(expected_full_sha256=after.hexdigest().upper(), offline_entries_verified=len(expected))
        results[role] = {'source_sha256': before.hexdigest().upper(), 'expected_sha256': after.hexdigest().upper(),
                         'independent_reader_verified_entries': len(expected), 'unrelated_encrypted_records_exact': True,
                         'opaque_tombstones_exact': True}
    managed = sandbox.read_jsonc(WORK/'managed-consumer-verification.json')
    if managed.get('Success') is not True: raise ValueError('Managed resource consumers have not passed')
    plan['offline_verification'] = results
    plan['managed_verification'] = {'path': str(WORK/'managed-consumer-verification.json'),
                                    'sha256': digest(WORK/'managed-consumer-verification.json')}
    tools = ['aa10_sandbox_zone.py', 'aa10_sandbox_scenarios.py', 'Aa10SandboxZonePak.py',
             'BuildAa10SandboxZoneEntry.py', 'BuildAa10SandboxZoneAssets.py', 'BuildAa10SandboxZoneCatalog.py']
    plan['tool_sources'] = [{'path': str(sandbox.REPO/'Scripts'/name), 'sha256': digest(sandbox.REPO/'Scripts'/name)} for name in tools]
    plan['state'] = 'offline-verified-native-test-pending'
    sandbox.write_json(path, plan)
    sandbox.write_json(WORK/'complete-package-rehearsal.json', results)
    print(json.dumps({'plan': str(path), 'sha256': digest(path), 'proof': results}, indent=2))
    return plan


def verify_packaged_resources(plan, directory):
    result = {}
    for role, record in plan['packages'].items():
        package_plan = sandbox.read_jsonc(record['manifest'])
        expected = {entry['entry']: entry['after_sha256'] for entry in package_plan['entries']}
        expected.update(record['sentinels'])
        extracted = extract(package_plan['package_path'], list(expected), directory/role)
        if any(extracted[name]['sha256'] != sha.upper() for name, sha in expected.items()):
            raise ValueError(f'The independent package reader rejected the installed {role} resources')
        result[role] = {'verified_entries': len(expected), 'sentinels': record['sentinels']}
    return result


def activate(path, expected_sha, authorize=False):
    if not authorize:
        raise ValueError('Explicit authorization is required to replace only sandbox379 with Zone411 and recover379 if needed')
    import msvcrt
    with (ROOT/'temp/launcher.lock').open('a+b') as lock:
        if lock.seek(0, os.SEEK_END) == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error: raise RuntimeError('Espera al arranque actual antes de cambiar de escenario.') from error
        try: return _activate_locked(path, expected_sha, authorize)
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def _activate_locked(path, expected_sha, authorize=False):
    if not authorize:
        raise ValueError('Explicit authorization is required to replace only sandbox379 with Zone411 and recover379 if needed')
    plan = load_plan(path, expected_sha)
    marker_path = ROOT/'zone411-installed.json'
    if marker_path.exists() and sandbox.read_jsonc(marker_path).get('deployment_sha256') == expected_sha.upper():
        sandbox.verify_runtime_binding(ROOT)
        return {'state': 'already-installed', 'zoneKey': 411}
    sandbox.verify_runtime_binding(ROOT)
    if scenes.selected(ROOT)['zoneKey'] != 379:
        raise ValueError('The reviewed switch starts only from the accepted Hall379')
    # Reuse the complete read-only rehearsal hashes only while the exact file identities still bind.
    compose_paths = [path for path in (ROOT/'compose.json', ROOT/'compose.watch.json') if path.exists()]
    compose_after = {str(path): replace_compose_bindings(sandbox.read_jsonc(path)) for path in compose_paths}
    for role, record in plan['packages'].items():
        package_plan = sandbox.read_jsonc(record['manifest'])
        if (not packages._matches_stat(packages._stat(Path(package_plan['package_path'])), package_plan['package_before']) or
                plan['offline_verification'][role]['source_sha256'] != package_plan['package_before']['sha256']):
            raise ValueError('The verified complete package hash no longer binds the exact source file')
        print('Identidad completa vigente, mismo archivo físico: '+role, flush=True)
    backup = secure_backup()
    configs = [*compose_paths, ROOT/'sandbox.json', ROOT/'autoentry-applied.json', marker_path,
               ROOT/'config/Configurations/ClientData.json', ROOT/'config/Configurations/MechanicsSandbox.json',
               ROOT/'config/Configurations/World.json', ROOT/'config/Configurations/InitialConfig.json']
    records = backup_files([*(record['target'] for record in plan['file_actions']), *configs], backup)
    sandbox.write_json(backup/'deployment-reference.json', {'plan': str(path), 'sha256': expected_sha})
    applied, old_position, interrupted, files_changed, position_changed = [], None, False, False, False
    try:
        live = sandbox.api(ROOT, '/api/world/zone-manager-status')
        if live.get('Players'):
            sandbox.command(ROOT, 'clear')
            sandbox.wait_for(lambda: sandbox.idle_result(ROOT), 'Retirada del Hall anterior', seconds=30)
        close_owned_client()
        interrupted = True
        sandbox.wait_for(lambda: not sandbox.api(ROOT, '/api/world/zone-manager-status').get('Players'),
                         'Cierre de la sesión anterior', seconds=30)
        processes = sandbox.sandbox_zone_processes(ROOT)
        if processes: sandbox.stop_owned_zone(ROOT, processes, planned_replacement=True)
        sandbox.compose(ROOT, 'stop', 'game')
        old_position = actor_position()
        sandbox.write_json(backup/'actor-position.json', old_position)
        for role, record in plan['packages'].items():
            packages.apply_plan(record['manifest'], allow_runtime=True, expected_manifest_sha256=record['sha256'])
            applied.append(role)
        files_changed = True
        for record in plan['file_actions']:
            target = owned_target(record['target']); target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(record['source'], target); ensure_hash(target, record['sha256'])
        proof = verify_packaged_resources(plan, backup/'verified-resources')
        profile = sandbox.read_jsonc(ROOT/'sandbox.json')
        profile.update(zoneKey=411, zoneName=scenes.LAB['zoneName'], origin=scenes.LAB['origin'],
                       scenarioPatch=PATCH_ID, deploymentManifest=str(path), deploymentSha256=expected_sha.upper())
        settings = sandbox.read_jsonc(ROOT/'config/Configurations/MechanicsSandbox.json')
        preset = sandbox.read_jsonc(sandbox.REPO/'Scripts/aa10_sandbox_training_hub_zone411.json')
        settings['MechanicsSandbox'].update({key: value for key, value in preset.items() if key != 'schema'})
        sandbox.write_json(ROOT/'config/Configurations/MechanicsSandbox.json', settings)
        sandbox.write_json(ROOT/'config/Configurations/ClientData.json', {'ClientData': {'Sources': ['ClientData', 'ClientData/game_pak']}})
        world_config = sandbox.read_jsonc(ROOT/'config/Configurations/World.json')
        world_config['World'].update(SpawnDoodads=False, SpawnTransfers=False, SpawnGimmicks=False)
        sandbox.write_json(ROOT/'config/Configurations/World.json', world_config)
        initial_path = ROOT/'config/Configurations/InitialConfig.json'
        sandbox.write_json(initial_path, lobby_configuration(sandbox.read_jsonc(initial_path)))
        for target, value in compose_after.items(): sandbox.write_json(target, value)
        print('Registrando hashes completos finales de los paquetes privados...', flush=True)
        identities = {role: dict(stats(ROOT/relative), sha256=digest(ROOT/relative)) for role, relative in
                      [('client', 'client/game_pak'), ('native', 'zone/game_pak')]}
        if any(identity['sha256'] != plan['packages'][role]['expected_full_sha256'] for role, identity in identities.items()):
            raise ValueError('The final complete package hash differs from the read-only deterministic rehearsal')
        old_marker = sandbox.read_jsonc(ROOT/'autoentry-applied.json')
        identity = identities['client']
        old_marker.update(package_path=identity['path'], package_size=identity['size'], package_mtime_ns=identity['mtime_ns'],
                          package_inode=identity['inode'], package_sha256=identity['sha256'], zone_key=411,
                          derived_zone_patch=PATCH_ID, stage_server_sha256=plan['driver']['after_sha256'],
                          state='verified-zone411-derivative')
        sandbox.write_json(ROOT/'autoentry-applied.json', old_marker)
        installed = {'schema': 1, 'patch_id': PATCH_ID, 'state': 'resources_verified', 'zoneKey': 411,
                     'zoneName': scenes.LAB['zoneName'], 'worldId': 0, 'packages': identities,
                     'deployment_sha256': expected_sha.upper(), 'deployment': str(path), 'backup': str(backup),
                     'resource_verification': proof, 'native_acceptance': 'pending user observation'}
        sandbox.write_json(marker_path, installed)
        sandbox.write_json(ROOT/'sandbox.json', profile)
        position_changed = True
        set_actor_position({'zone_id': 411,
                            **{axis.lower(): scenes.LAB['origin'][axis] for axis in ('X', 'Y', 'Z')},
                            'yaw': 0, 'pitch': 0, 'roll': 0})
        sandbox.verify_runtime_binding(ROOT); sandbox.validate_client(ROOT)
        sandbox.compose(ROOT, 'up', '-d', 'game')
        sandbox.wait_for(lambda: sandbox.api(ROOT, '/api/world/zone-manager-status'), 'Carga de World con la nueva Zone', seconds=600)
        sandbox.start_zone(ROOT, profile)
        sandbox.wait_for(lambda: sandbox.zone_ready(sandbox.api(ROOT, '/api/world/zone-manager-status'), 411),
                         'Carga nativa de la Zone411', seconds=180)
        sandbox.capture(ROOT, 'zone411-server-ready', {'success': True, 'deployment': str(path), 'backup': str(backup),
                        'world': sandbox.api(ROOT, '/api/world/zone-manager-status'),
                        'runtime': sandbox.api(ROOT, '/api/mechanics-sandbox/runtime')})
        return {'state': 'native-zone-ready', 'zoneKey': 411, 'backup': str(backup), 'client': 'user opens the normal sandbox shortcut'}
    except Exception as original:
        sandbox.write_json(backup/'failure-initial.json', {'error': str(original)})
        print('Falló la sustitución; recuperando el perfil anterior: '+str(original), flush=True)
        failures = []
        if interrupted:
            try:
                processes = sandbox.sandbox_zone_processes(ROOT)
                if processes: sandbox.stop_owned_zone(ROOT, processes, planned_replacement=True)
                sandbox.compose(ROOT, 'stop', 'game')
            except Exception as error: failures.append('stop: '+str(error))
        for role in reversed(applied):
            record = plan['packages'][role]
            try: packages.rollback_plan(record['manifest'], allow_runtime=True, expected_manifest_sha256=record['sha256'])
            except Exception as error: failures.append(role+' rollback: '+str(error))
        try:
            if files_changed: restore_files(records)
            if position_changed and old_position: set_actor_position(old_position)
        except Exception as error: failures.append('files/position: '+str(error))
        if interrupted and not failures:
            try:
                sandbox.compose(ROOT, 'up', '-d', 'game')
                sandbox.wait_for(lambda: sandbox.api(ROOT, '/api/world/zone-manager-status'), 'Recuperación del Hall379', seconds=600)
                sandbox.start_zone(ROOT, sandbox.read_jsonc(ROOT/'sandbox.json'))
                sandbox.wait_for(lambda: sandbox.zone_ready(sandbox.api(ROOT, '/api/world/zone-manager-status')),
                                 'Recuperación nativa del Hall379', seconds=180)
            except Exception as error: failures.append('server recovery: '+str(error))
        sandbox.write_json(backup/'failure.json', {'error': str(original), 'rollback_errors': failures})
        raise RuntimeError(f'Zone411 no se aceptó: {original}. Backup: {backup}. Rollback: {failures or "perfil anterior recuperado"}') from original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    staging = sub.add_parser('prepare'); staging.add_argument('--output', type=Path, required=True)
    proving = sub.add_parser('prove'); proving.add_argument('--plan', type=Path, required=True)
    activation = sub.add_parser('activate'); activation.add_argument('--plan', type=Path, required=True)
    activation.add_argument('--expected-sha256', required=True)
    activation.add_argument('--authorize-zone411-test-and-379-rollback', action='store_true')
    args = parser.parse_args()
    os.environ.update(sandbox.execution_env(ROOT))
    if args.action == 'prepare': prepare(args.output)
    elif args.action == 'prove': prove(args.plan)
    elif args.action == 'activate':
        print(json.dumps(activate(args.plan, args.expected_sha256, args.authorize_zone411_test_and_379_rollback), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
