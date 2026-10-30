"""Local AA10 r575 sandbox orchestrator. All owned files stay on drive E.

The regular aaemu10 stack is read only: a consistent SQL snapshot seeds a
separate Compose project, and the Spanish client is physically copied.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import aa10_sandbox_scenarios as scenes

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
DEFAULT_ROOT = PROJECT / 'runtime/sandbox-aa10'
SOURCE_CLIENT = PROJECT / 'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview'
SOURCE_ZONE = PROJECT / 'zones/retail-zone-server-r575'
COMPOSE_PROJECT = 'aaemu10-sandbox'
CHARACTER_ID, ACCOUNT_ID = 1001, 1
CHARACTER_NAME, SOURCE_NAME = 'Sandbox', 'Wingsjuanka'
ORIGIN = {'X': 500.295, 'Y': 38373.5, 'Z': 129.948, 'Rotation': 0.0}
ZONE_HASH = '8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a'
PORTS = {'login': 3237, 'game': 3239, 'stream': 3250, 'world': 3240}


def timestamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def read_jsonc(path):
    """Strip JSON comments without mistaking URL/string contents for comments."""
    text = Path(path).read_text(encoding='utf-8-sig')
    output, index, quoted, escaped = [], 0, False, False
    while index < len(text):
        char = text[index]
        if quoted:
            output.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            index += 1
        elif char == '"':
            quoted = True
            output.append(char)
            index += 1
        elif text.startswith('//', index):
            end = text.find('\n', index)
            index = len(text) if end < 0 else end
        elif text.startswith('/*', index):
            end = text.find('*/', index + 2)
            if end < 0:
                raise ValueError('Unterminated configuration comment')
            output.append(' ')
            index = end + 2
        else:
            output.append(char)
            index += 1
    return json.loads(''.join(output))


def safe_root(value):
    requested = Path(value).absolute()
    root = requested.resolve()
    runtime = (PROJECT/'runtime').resolve()
    if root.drive.upper() != 'E:' or root == runtime or not root.is_relative_to(runtime):
        raise ValueError(f'Sandbox root must stay inside {runtime} on E:')
    if requested.exists() and (requested.is_symlink() or requested.is_junction()):
        raise ValueError('Sandbox root must be a physical directory')
    return root


def execution_env(root):
    env = dict(os.environ)
    temp = root / 'temp'
    temp.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp),
               PYTHONDONTWRITEBYTECODE='1', DOTNET_CLI_TELEMETRY_OPTOUT='1',
               DOTNET_GENERATE_ASPNET_CERTIFICATE='false', DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',
               DOTNET_CLI_HOME=str(PROJECT / 'artifacts/sandbox/dotnet-home'),
               NUGET_PACKAGES=str(PROJECT / 'artifacts/cache/nuget'),
               npm_config_cache=str(PROJECT / 'artifacts/cache/npm'))
    return env


def run(args, *, root=DEFAULT_ROOT, input_bytes=None, stdout=None, check=True):
    result = subprocess.run([str(arg) for arg in args], input=input_bytes,
                            stdout=stdout if stdout is not None else subprocess.PIPE,
                            stderr=subprocess.PIPE, env=execution_env(root), cwd=REPO)
    if check and result.returncode:
        diagnostic = result.stderr.decode('utf-8', errors='replace')[-3000:]
        raise RuntimeError(f'{args[0]} exited {result.returncode}: {diagnostic}')
    return result


def compose(root, *arguments, **kwargs):
    path = root/'compose.watch.json' if (root/'watch-mode.json').exists() else root/'compose.json'
    return run(['docker', 'compose', '-p', COMPOSE_PROJECT, '-f', path,
                *arguments], root=root, **kwargs)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def copy_missing(source, destination, excluded=()):
    destination.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        if entry.name in excluded or entry.name.endswith(('.log', '.bak')):
            continue
        if entry.is_symlink() or entry.is_junction():
            # Never clone Windows Documents/profile aliases or a recursive link.
            continue
        target = destination / entry.name
        if entry.is_dir():
            copy_missing(entry, target, excluded)
        elif not target.exists():
            shutil.copy2(entry, target)


def select_lan_address(root):
    # Native r575 rejects loopback for world_serveraddr. Preserve the already
    # working LAN address, exposing only the separate authority port there.
    text = (SOURCE_ZONE/'system.cfg').read_text(encoding='utf-8-sig')
    match = re.search(r'world_serveraddr\s*=\s*"([0-9.]+)"', text)
    if not match or match.group(1).startswith('127.'):
        raise ValueError('A verified native non-loopback World address is required')
    address = match.group(1)
    with socket.socket() as probe:
        probe.bind((address, 0))
    return address


def make_compose(root, lan, password, login_image):
    bind = lambda source, target, readonly=True: {
        'type': 'bind', 'source': str(source).replace('\\', '/'),
        'target': target, 'read_only': readonly}
    return {'services': {
        'db': {'image': 'mysql:8.0.36', 'restart': 'unless-stopped',
               'environment': {'MYSQL_ROOT_PASSWORD': password},
               'volumes': [bind(root/'db', '/var/lib/mysql', False)],
               'healthcheck': {'test': ['CMD-SHELL', 'mysqladmin ping -h127.0.0.1 -uroot -p"$$MYSQL_ROOT_PASSWORD"'],
                               'interval': '3s', 'timeout': '5s', 'retries': 40},
               'logging': {'driver': 'none'}},
        'login': {'image': login_image, 'restart': 'unless-stopped',
                  'depends_on': {'db': {'condition': 'service_healthy'}},
                  'ports': ['127.0.0.1:3237:1237'],
                  'volumes': [bind(root/'config/Login.json', '/app/Config.json'),
                              bind(root/'logs/login', '/app/Logs', False)],
                  'environment': {'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT': '1'},
                  'logging': {'driver': 'json-file', 'options': {'max-size': '5m', 'max-file': '2'}}},
        'game': {'image': 'aaemu10-sandbox-world:local', 'restart': 'unless-stopped',
                 'build': {'context': str(REPO).replace('\\', '/'),
                           'dockerfile': 'AAEmu.WorldServer/AAEmu.World/Dockerfile',
                           'args': {'CONFIGURATION': 'Release'}},
                 'depends_on': {'db': {'condition': 'service_healthy'}, 'login': {'condition': 'service_started'}},
                 'ports': ['127.0.0.1:3239:1239', '127.0.0.1:3250:1250', f'{lan}:3240:1240'],
                 'environment': {'GameContentRoot': '/app/game',
                                 'ZoneGameDataRoot': '/app/game/ClientData/game',
                                 'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT': '1'},
                 'volumes': [bind(SOURCE_CLIENT, '/app/game/ClientData'),
                             bind(REPO/'.server_files/AAEmu.Game/Data', '/app/game/Data'),
                             bind(root/'config/Configurations', '/app/game/Configurations'),
                             bind(root/'config/Game.json', '/app/game/Config.json'),
                             bind(root/'config/World.json', '/app/Config.json'),
                             bind(root/'logs/game', '/app/game/Logs', False)],
                 'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '2'}}}}}


def prepare(root):
    for relative in ['config/Configurations', 'logs/game', 'logs/login', 'backups', 'captures', 'profile']:
        (root/relative).mkdir(parents=True, exist_ok=True)
    profile_file = root/'sandbox.json'
    if profile_file.exists():
        profile = read_jsonc(profile_file)
        if profile.get('schema') != 1 or profile.get('characterId') != CHARACTER_ID:
            raise ValueError('Unknown sandbox profile; refusing to replace it')
        verify_runtime_binding(root)
        shortcuts(root)
        return profile
    lan = select_lan_address(root)
    print('Preparando copia física del cliente español y runtime nativo en E...', flush=True)
    copy_missing(SOURCE_CLIENT, root/'client', {'GPUCache', '.aa10-local-profile-backup'})
    for directory in ['Bin64', 'game']:
        copy_missing(SOURCE_ZONE/directory, root/'zone'/directory,
                     {'backups', '.zonehost-updates', 'gameguard', 'xigncode'})
    if not (root/'zone/game_pak').exists():
        shutil.copy2(SOURCE_ZONE/'game_pak', root/'zone/game_pak')
    native = root/'zone/Bin64/x2game-dev_dedicate.dll'
    if sha256(native) != ZONE_HASH:
        raise ValueError('Native Zone DLL differs from accepted gatekeeper379 identity')
    (root/'zone/system.cfg').write_text(f'world_serveraddr = "{lan}"\nworld_serverport = 3240\n', encoding='utf-8')
    (root/'profile/system.cfg').write_text('locale = en_us\nr_Width = 1280\nr_Height = 720\nr_Fullscreen = 0\n', encoding='utf-8')
    shutil.copytree(REPO/'.server_files/AAEmu.Game/Configurations', root/'config/Configurations', dirs_exist_ok=True)
    # Bind both catalogue and behaviour to the dedicated cloned actor only.
    sandbox_config = read_jsonc(REPO/'AAEmu.Game/Configurations/MechanicsSandbox.json')
    settings = sandbox_config['MechanicsSandbox']
    settings.update(Enabled=True, CharacterName=CHARACTER_NAME, CharacterId=CHARACTER_ID,
                    AccountId=ACCOUNT_ID, ZoneKey=379, WorldId=0, InstanceId=0, Origin=ORIGIN)
    from aa10_sandbox_hub import plan as plan_hub, PRESET
    sandbox_config = plan_hub(sandbox_config, read_jsonc(PRESET))
    write_json(root/'config/Configurations/MechanicsSandbox.json', sandbox_config)
    password, secret = secrets.token_hex(24), secrets.token_hex(24)
    connection = {'MySQLProvider': {'Host': 'db', 'Port': '3306', 'User': 'root',
                                   'Password': password, 'Database': 'aaemu_game'}, 'AutoApplyUpdates': True}
    game = read_jsonc(REPO/'.server_files/AAEmu.Game/Config.json')
    game.update(SecretKey=secret, Connections=connection, DebugInfo=False)
    game['Network'].update(Host='*', Port=1239)
    game['StreamNetwork'].update(Host='*', Port=1250, AdvertisedPort=3250)
    game['LoginNetwork'].update(Host='login', Port=1234)
    write_json(root/'config/Game.json', game)
    login = read_jsonc(REPO/'.server_files/AAEmu.Login/Config.json')
    login.update(SecretKey=secret, SkipHostResolve=True)
    login['Connections'] = json.loads(json.dumps(connection))
    login['Connections']['MySQLProvider']['Database'] = 'aaemu_login'
    login['GameServers'] = [{'Id': 1, 'Name': 'AA10 Sandbox', 'Host': '127.0.0.1', 'Port': 3239}]
    login['Network'].update(Host='*', Port=1237)
    login['InternalNetwork'].update(Host='*', Port=1234)
    write_json(root/'config/Login.json', login)
    world = read_jsonc(REPO/'AAEmu.WorldServer/AAEmu.World/Config.json')
    world['PublicNetwork'].update(Host='127.0.0.1', Port=3239)
    world.update(GameContentRoot='/app/game', ZoneGameDataRoot='/app/game/ClientData/game')
    world['ZoneHost']['Enabled'] = False
    write_json(root/'config/World.json', world)
    login_image = run(['docker', 'inspect', 'aaemu10-login-1', '--format', '{{.Config.Image}}'], root=root).stdout.decode().strip()
    write_json(root/'compose.json', make_compose(root, lan, password, login_image))
    profile = {'schema': 1, 'createdAtUtc': timestamp(), 'composeProject': COMPOSE_PROJECT,
               'characterId': CHARACTER_ID, 'accountId': ACCOUNT_ID, 'character': CHARACTER_NAME,
               'username': 'test', 'sourceCharacter': SOURCE_NAME, 'zoneKey': 379,
               'zoneName': 'gatekeeper_hall', 'origin': ORIGIN, 'worldHost': lan, 'ports': PORTS,
               'sourceClient': str(SOURCE_CLIENT), 'client': str(root/'client'),
               'nativeDllSha256': ZONE_HASH}
    write_json(profile_file, profile)
    shortcuts(root)
    return profile


def verify_runtime_binding(root):
    config = read_jsonc(root/'config/Configurations/MechanicsSandbox.json')['MechanicsSandbox']
    scene = scenes.selected(root)
    expected = {'Enabled': True, 'CharacterName': CHARACTER_NAME, 'CharacterId': CHARACTER_ID,
                'AccountId': ACCOUNT_ID, 'ZoneKey': scene['zoneKey'], 'WorldId': 0, 'InstanceId': 0}
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError('Sandbox actor binding changed; refusing to alter or launch another scenario')
    scenes.verify_installation(root)


def shortcuts(root):
    script = REPO/'Scripts/Start-AA10Sandbox.ps1'
    for filename, arguments in [('Iniciar sandbox AA10.cmd', '-StartZone'),
                                 ('Diagnosticar pantalla negra.cmd', '-StartZone -VisibleClient'),
                                 ('Comprobar cierre del panel.cmd', '-Action panel-check'),
                                 ('Aplicar laboratorio de entrenamiento.cmd', '-Action hub'),
                                 ('Herramienta de desarrollo.cmd', '-Action tool'),
                                 ('Reiniciar escenario.cmd', '-Action reset'),
                                 ('Estado sandbox.cmd', '-Action status')]:
        content = f'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script}" {arguments}\r\nif errorlevel 1 pause\r\n'
        if filename == 'Comprobar cierre del panel.cmd':
            content = content.replace('if errorlevel 1 pause', 'pause')
        if filename == 'Herramienta de desarrollo.cmd':
            interpreter = Path(sys.executable).with_name('pythonw.exe')
            if interpreter.exists():
                content = (f'@echo off\r\nset "TEMP={root / "temp"}"\r\nset "TMP={root / "temp"}"\r\n'
                           'set "PYTHONDONTWRITEBYTECODE=1"\r\nset "PYTHONUTF8=1"\r\n'
                           f'start "" "{interpreter}" -B "{REPO / "Scripts/aa10_sandbox.py"}" tool\r\n')
        path = root/filename
        if not path.exists() or path.read_bytes() != content.encode('ascii'):
            path.write_bytes(content.encode('ascii'))


def seed(root):
    marker = root/'seed.json'
    if marker.exists():
        print('La base aislada ya está preparada; se conserva su estado.', flush=True)
        return
    compose(root, 'up', '-d', 'db')
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        result = run(['docker', 'exec', COMPOSE_PROJECT+'-db-1', 'sh', '-c',
                      'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h127.0.0.1 -uroot --batch --skip-column-names -e "SELECT 1"'], root=root, check=False)
        if result.returncode == 0:
            break
        time.sleep(2)
    else:
        raise TimeoutError('Sandbox MySQL did not become ready')
    source_state = run(['docker', 'exec', 'aaemu10-game-1', 'wget', '-qO-',
                        'http://127.0.0.1:1280/api/character/list?Name='+SOURCE_NAME], root=root)
    characters = json.loads(source_state.stdout)
    if len(characters) != 1 or characters[0].get('Id') != CHARACTER_ID or characters[0].get('IsOnline'):
        raise ValueError('The exact source character must exist and be offline before snapshotting')
    snapshot = root/'backups'/f'source-snapshot-{timestamp()}.sql'
    with snapshot.open('wb') as output:
        run(['docker', 'exec', 'aaemu10-db-1', 'sh', '-c',
             'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --skip-lock-tables '
             '--hex-blob --set-gtid-purged=OFF --databases aaemu_login aaemu_game'], root=root, stdout=output)
    with snapshot.open('rb') as source:
        result = subprocess.run(['docker', 'exec', '-i', COMPOSE_PROJECT+'-db-1', 'sh', '-c',
                                 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h127.0.0.1 -uroot'], stdin=source,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=execution_env(root))
    if result.returncode:
        raise RuntimeError('Import of sandbox snapshot failed: '+result.stderr.decode(errors='replace')[-1500:])
    # This SQL is sent only to the isolated container, never the source DB.
    sql = f'''START TRANSACTION;
UPDATE aaemu_game.characters SET name='Sandbox',access_level=100,world_id=0,zone_id=379,
x={ORIGIN['X']},y={ORIGIN['Y']},z={ORIGIN['Z']},yaw=0,pitch=0,roll=0,
family=0,expedition_id=0,deleted=0
WHERE id=1001 AND account_id=1 AND name='Wingsjuanka';
SELECT ROW_COUNT();
UPDATE aaemu_game.characters SET deleted=1 WHERE id<>1001;
COMMIT;
SELECT id,account_id,name,zone_id FROM aaemu_game.characters WHERE deleted=0;
'''
    result = run(['docker', 'exec', '-i', COMPOSE_PROJECT+'-db-1', 'sh', '-c',
                  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h127.0.0.1 -uroot --batch --skip-column-names'],
                 root=root, input_bytes=sql.encode())
    rows = result.stdout.decode().strip().splitlines()
    if rows != ['1', '1001\t1\tSandbox\t379']:
        raise RuntimeError(f'Sandbox seed identity rejected: {rows}')
    write_json(marker, {'snapshot': str(snapshot), 'snapshotSha256': sha256(snapshot),
                       'characterId': CHARACTER_ID, 'accountId': ACCOUNT_ID, 'character': CHARACTER_NAME})


def api(root, endpoint, body=None):
    args = ['docker', 'exec', COMPOSE_PROJECT+'-game-1', 'wget', '-qO-', '-T', '10']
    if body is not None:
        args += ['--header=Content-Type: application/json', '--post-data='+json.dumps(body)]
    result = run(args+['http://127.0.0.1:1280'+endpoint], root=root)
    return json.loads(result.stdout)


def credential_material():
    # A local launcher proof is sufficient; no plaintext password is retained.
    digest = secrets.token_bytes(32)
    return {'schema': 1, 'username': 'test',
            'token': 'aaemu-sha256-v1:'+digest.hex().upper(),
            'storage': base64.b64encode(digest).decode('ascii')}


def ensure_credentials(root):
    label = run(['docker', 'inspect', COMPOSE_PROJECT+'-db-1', '--format',
                 '{{index .Config.Labels "com.docker.compose.project"}}'], root=root).stdout.decode().strip()
    if label != COMPOSE_PROJECT:
        raise ValueError('Refusing credential update outside the isolated sandbox DB')
    seed_identity = read_jsonc(root/'seed.json')
    if (seed_identity.get('characterId'), seed_identity.get('accountId')) != (CHARACTER_ID, ACCOUNT_ID):
        raise ValueError('Sandbox seed identity differs from the fixed actor')
    directory = root/'secrets'
    if directory.exists() and (directory.is_symlink() or directory.is_junction()):
        raise ValueError('Sandbox secrets directory must be physical and on E')
    directory.mkdir(exist_ok=True)
    if os.name == 'nt':
        principal = os.environ.get('USERDOMAIN', '')+'\\'+os.environ['USERNAME']
        secured = run(['icacls', directory, '/inheritance:r', '/grant:r',
                       principal+':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], root=root, check=False)
        if secured.returncode:
            raise RuntimeError('Could not protect the sandbox credential directory')
    path = directory/'launcher-auth.json'
    value = read_jsonc(path) if path.exists() else credential_material()
    token = str(value.get('token', ''))
    if value.get('schema') != 1 or value.get('username') != 'test' or not re.fullmatch(r'aaemu-sha256-v1:[0-9A-Fa-f]{64}', token):
        raise ValueError('Unknown sandbox launcher credential format')
    storage = base64.b64encode(bytes.fromhex(token.split(':', 1)[1])).decode('ascii')
    if value.get('storage') != storage:
        raise ValueError('Sandbox launcher credential is inconsistent')
    sql = ("UPDATE aaemu_login.users SET password='"+storage+"' WHERE id=1 AND username='test';\n"
           "SELECT COUNT(*) FROM aaemu_login.users WHERE id=1 AND username='test' AND password='"+storage+"';\n")
    # stdin prevents a proof/password from appearing in process arguments. Do not
    # propagate database diagnostics, which could quote the offending SQL.
    result = run(['docker', 'exec', '-i', COMPOSE_PROJECT+'-db-1', 'sh', '-c',
                  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h127.0.0.1 -uroot --batch --skip-column-names'],
                 root=root, input_bytes=sql.encode('ascii'), check=False)
    if result.returncode or result.stdout.decode().strip() != '1':
        raise RuntimeError('Sandbox credential initialization failed; no credential was logged')
    if not path.exists():
        write_json(path, value)
    return token


def command(root, action):
    result = api(root, '/api/mechanics-sandbox/'+action, {'character': CHARACTER_NAME})
    if result.get('state') in ('faulted', 'rejected'):
        raise ValueError(result.get('message', 'Sandbox scenario faulted'))
    if not result.get('success'):
        raise RuntimeError(result.get('message', 'Sandbox command rejected'))
    return result


def zone_ready(value, zone_key=379):
    now = dt.datetime.now(dt.timezone.utc)
    for zone in value.get('Zones', []):
        if zone.get('ZoneId') != zone_key or zone.get('InstanceId') != 0 or zone.get('State') != 'ZoneLoaded':
            continue
        heartbeat = zone.get('LastHeartbeatAtUtc')
        if heartbeat and 0 <= (now-dt.datetime.fromisoformat(heartbeat.replace('Z', '+00:00'))).total_seconds() <= 6:
            return True
    return False


def wait_for(predicate, description, seconds=240):
    started = time.monotonic()
    deadline, last, next_notice = started+seconds, None, started+15
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (RuntimeError, json.JSONDecodeError) as error:
            last = str(error)
        if time.monotonic() >= next_notice:
            print(f'{description}: esperando ({int(time.monotonic()-started)} s)...', flush=True)
            next_notice = time.monotonic()+15
        time.sleep(2)
    raise TimeoutError(f'{description}: {last or "timeout"}')


def start_zone(root, profile):
    # Only this dedicated copy and exact gatekeeper profile can be started.
    executable = root/'zone/Bin64/AAEmu.ZoneHost.exe'
    scene = scenes.definition(profile.get('zoneKey', 379))
    helper = PROJECT/'tools/AAEmu.ControlCenter/resources/native/win-x64/AAEmu.ZoneProcessHost.exe'
    if sha256(root/'zone/Bin64/x2game-dev_dedicate.dll') != ZONE_HASH:
        raise ValueError('Native DLL changed; refusing Zone startup')
    processes = sandbox_zone_processes(root)
    if processes:
        try:
            wait_for(lambda: zone_ready(api(root, '/api/world/zone-manager-status'), scene['zoneKey']),
                     'Reconexión de la Zone del sandbox', seconds=12)
            return
        except TimeoutError:
            stop_owned_zone(root, processes)
    env = execution_env(root)
    env.update(AAEMU_ZONE_DLL=str(root/'zone/Bin64/x2game-dev_dedicate.dll'),
               AAEMU_ZONE_SAVE_DIR=str(root/'zone-save'), AAEMU_ZONE_LOG_NAME=f"sandbox-{scene['zoneKey']}")
    (root/'zone-save').mkdir(exist_ok=True)
    args = [str(helper), str(executable), '+zone', scene['zoneName'],
            '+world_serveraddr', profile['worldHost'], '+world_serverport', '3240',
            '+sv_port', '65479']
    if scene['zoneKey'] == 411:
        args += ['+db_location', str(root/'zone/game/db/compact.sqlite3')]
    process = subprocess.Popen(args, cwd=executable.parent, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    write_json(root/'zone-owner.json', {'helperPid': process.pid, 'executable': str(executable),
                                      'requestedAtUtc': timestamp(), 'zoneKey': scene['zoneKey'], 'worldPort': 3240})


def sandbox_zone_processes(root):
    executable = str(root/'zone/Bin64/AAEmu.ZoneHost.exe').replace("'", "''")
    script = ("$target='"+executable+"'; @((Get-CimInstance Win32_Process -Filter \"Name='AAEmu.ZoneHost.exe' OR Name='AAEmu.ZoneProcessHost.exe'\") "
              "| Where-Object { $_.ExecutablePath -eq $target -or "
              "($_.Name -eq 'AAEmu.ZoneProcessHost.exe' -and $_.CommandLine -and $_.CommandLine.Contains($target)) } "
              "| Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,@{n='CreatedUtc';e={$_.CreationDate.ToUniversalTime().ToString('o')}}) | ConvertTo-Json -Compress")
    result = run(['powershell.exe', '-NoProfile', '-Command', script], root=root)
    text = result.stdout.decode('utf-8', errors='replace').strip()
    value = json.loads(text) if text else []
    return value if isinstance(value, list) else [value]


def owned_process_guard(process, *, stop=True):
    """Compare real UTC instants, not serialized fractional-second spellings."""
    expected_path = process['ExecutablePath'].replace("'", "''")
    created = process['CreatedUtc'].replace("'", "''")
    return (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={process['ProcessId']}'; "
            "if (!$p) { Write-Output 'already-exited'; exit 0 }; "
            f"$expectedTicks=([DateTimeOffset]::Parse('{created}')).UtcDateTime.Ticks; "
            f"if ($p.ExecutablePath -ne '{expected_path}' -or "
            "$p.CreationDate.ToUniversalTime().Ticks -ne $expectedTicks) { throw 'Sandbox process identity changed' }; " +
            ("Stop-Process -Id $p.ProcessId -ErrorAction Stop; Write-Output 'stopped'" if stop else "Write-Output 'identity-confirmed'"))


def stop_owned_zone(root, processes, *, planned_replacement=False):
    """Recover only the exact, unhealthy sandbox process pair recorded by this launcher."""
    owner = read_jsonc(root/'zone-owner.json')
    executable = str(root/'zone/Bin64/AAEmu.ZoneHost.exe')
    helper_path = str(PROJECT/'tools/AAEmu.ControlCenter/resources/native/win-x64/AAEmu.ZoneProcessHost.exe')
    scene = scenes.selected(root)
    if owner.get('executable') != executable or owner.get('zoneKey') != scene['zoneKey'] or owner.get('worldPort') != 3240:
        raise ValueError('Sandbox Zone ownership binding differs; refusing process recovery')
    requested = dt.datetime.strptime(owner['requestedAtUtc'], '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
    helpers = [p for p in processes if p['ProcessId'] == owner.get('helperPid')
               and p['ExecutablePath'].casefold() == helper_path.casefold()]
    children = [p for p in processes if p['ExecutablePath'].casefold() == executable.casefold()
                and p['ParentProcessId'] == owner.get('helperPid')]
    if len(helpers) != 1 or len(children) != 1 or len(processes) != 2:
        raise ValueError('Unrecognized sandbox Zone processes; refusing process recovery')
    for process in [*children, *helpers]:
        created = dt.datetime.fromisoformat(process['CreatedUtc'].replace('Z', '+00:00'))
        if abs((created-requested).total_seconds()) > 15:
            raise ValueError('Sandbox Zone PID ownership expired; refusing process recovery')
    # Recheck identity immediately before each stop to reject PID reuse.
    outcomes = []
    for process in [*children, *helpers]:
        script = owned_process_guard(process)
        result = run(['powershell.exe', '-NoProfile', '-Command', script], root=root).stdout.decode().strip()
        if result not in ('stopped', 'already-exited'):
            raise ValueError('Unexpected sandbox process retirement result')
        outcomes.append({'pid': process['ProcessId'], 'state': result})
    capture(root, 'zone-recovery', {'zoneKey': scene['zoneKey'],
                                    'stoppedPids': [item['pid'] for item in outcomes if item['state'] == 'stopped'],
                                    'processOutcomes': outcomes,
                                    'reason': 'authorized scene replacement' if planned_replacement else 'unhealthy World reconnection'})
    print(f"Finalizó el retiro de la Zone {scene['zoneKey']} del sandbox para " +
          ('el cambio autorizado de escenario.' if planned_replacement else 'recuperar su conexión.'), flush=True)


def validate_client(root):
    profile = read_jsonc(root/'client/.aa10-sandbox-profile.json')
    if profile.get('patchId') != 'aa10-sandbox-e-profile-v1' or Path(profile.get('profilePath', '')).resolve() != (root/'profile').resolve():
        raise ValueError('Sandbox client profile does not point to its own directory on E')
    if sha256(root/'client/Bin64/xlcommon.dll') != str(profile.get('currentSha256', '')).lower():
        raise ValueError('Sandbox profile DLL changed; inspect the profile patch before launching')
    marker = read_jsonc(root/'autoentry-applied.json')
    if marker.get('patch_id') != 'aa10-sandbox-autoentry-v3':
        raise ValueError('Apply the verified V3 sandbox entry driver before launching this client')
    scene = scenes.selected(root)
    if (marker.get('character'), marker.get('world_id'), marker.get('zone_key')) != (CHARACTER_NAME, 1, scene['zoneKey']):
        raise ValueError('Client autoentry binding differs from this sandbox')
    package = root/'client/game_pak'
    if Path(marker.get('package_path', '')).resolve() != package.resolve():
        raise ValueError('Client autoentry marker names another package')
    identity = package.stat()
    if (identity.st_size != marker.get('package_size') or identity.st_mtime_ns != marker.get('package_mtime_ns')
            or identity.st_ino != marker.get('package_inode')):
        raise ValueError('Sandbox package changed since patch verification; rerun the client patch verifier')
    if package.samefile(SOURCE_CLIENT/'game_pak'):
        raise ValueError('The sandbox package must be physically independent of the main client')
    if sha256(root/'client/Bin64/x2game.dll') != str(marker.get('x2game_sha256', '')).lower():
        raise ValueError('Client x2game identity changed since autoentry acceptance')


def start(root, authorize_zone=False, no_client=False, visible_client=False):
    import msvcrt
    (root/'temp').mkdir(parents=True, exist_ok=True)
    with (root/'temp/launcher.lock').open('a+b') as lock:
        if lock.seek(0, os.SEEK_END) == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('El sandbox ya tiene un arranque en curso; espera a que termine.') from error
        try:
            return _start(root, authorize_zone, no_client, visible_client)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def close_disconnected_client(root):
    """Called only after this sandbox's World registry confirms its actor is offline."""
    target = str(root/'client/Bin64/archeage.exe').replace("'", "''")
    script = (f"$target='{target}'; $owned=@(Get-CimInstance Win32_Process -Filter \"Name='archeage.exe'\" "
              '| Where-Object {$_.ExecutablePath -eq $target}); '
              'foreach($candidate in $owned) { '
              '$current=Get-CimInstance Win32_Process -Filter (\'ProcessId=\'+$candidate.ProcessId); '
              'if($current -and $current.ExecutablePath -eq $target -and '
              '$current.CreationDate -eq $candidate.CreationDate) { '
              'Stop-Process -Id $current.ProcessId -ErrorAction Stop } }')
    run(['powershell.exe', '-NoProfile', '-Command', script], root=root)


def client_running(root):
    target = str(root/'client/Bin64/archeage.exe').replace("'", "''")
    script = (f"$target='{target}'; $owned=@(Get-CimInstance Win32_Process -Filter \"Name='archeage.exe'\" "
              "| Where-Object {$_.ExecutablePath -eq $target}); if ($owned.Count -gt 0) {'yes'} else {'no'}")
    return run(['powershell.exe', '-NoProfile', '-Command', script], root=root).stdout.decode().strip() == 'yes'


def _start(root, authorize_zone=False, no_client=False, visible_client=False):
    profile = prepare(root)
    scene = scenes.selected(root)
    if not no_client and not (root/'client/.aa10-sandbox-profile.json').exists():
        raise RuntimeError('Apply the E-only sandbox profile patch before launching the client')
    if not no_client and not (root/'autoentry-applied.json').exists():
        raise RuntimeError('Apply/verify the sandbox autoentry patch and record autoentry-applied.json first')
    if not no_client:
        validate_client(root)
    seed(root)
    compose(root, 'up', '-d', 'login', 'game')
    token = ensure_credentials(root)
    print('Comprobando World del sandbox; si se está reiniciando, esperaré su carga de datos...', flush=True)
    status = wait_for(lambda: api(root, '/api/world/zone-manager-status'), 'Carga de World del sandbox', seconds=600)
    if not zone_ready(status, scene['zoneKey']):
        if not authorize_zone:
            raise RuntimeError(f"Zone{scene['zoneKey']} no está lista. Autoriza sólo el perfil activo con --start-zone.")
        start_zone(root, profile)
        wait_for(lambda: zone_ready(api(root, '/api/world/zone-manager-status'), scene['zoneKey']), f"Carga de Zone{scene['zoneKey']}")
    if no_client:
        return
    status = api(root, '/api/world/zone-manager-status')
    previous_actor = next((p.get('ObjectId') for p in status.get('Players', []) if p.get('Id') == CHARACTER_ID), None)
    if not client_running(root) or previous_actor is None:
        close_disconnected_client(root)
        client = root/'client/Bin64/archeage.exe'
        args = [str(client), '-devmode', '-nosplash', '-StrUserName=test', '-strUserToken='+token,
                '-sIp=127.0.0.1', '-sPort=3237', '-gameId=1', '+locale', 'en_us',
                '+client_default_zone', str(scene['zoneKey'])]
        client_env = execution_env(root)
        for key, relative in [('APPDATA', 'appdata/roaming'), ('LOCALAPPDATA', 'appdata/local')]:
            directory = root/relative
            directory.mkdir(parents=True, exist_ok=True)
            client_env[key] = str(directory)
        from aa10_sandbox_window import LoadingClient, VisibleClient
        presentation = (VisibleClient(args, cwd=client.parent, env=client_env) if visible_client else
                        LoadingClient(args, cwd=client.parent, env=client_env))
        client_process = presentation.process
        capture(root, 'client-launch', {'pid': client_process.pid, 'createdAtUtc': timestamp(),
                                       'presentation': 'visible-diagnostic' if visible_client else 'own-loading-panel-normal-game-window', 'noSplash': True,
                                       'characterId': CHARACTER_ID, 'zoneKey': scene['zoneKey']})
        print('Preparando el cliente español; la ventana aparecerá al estar listo...', flush=True)
    else:
        client_process = None
        presentation = None
    def character_entered():
        # The typed endpoint resolves the active Game connection and validates
        # WorldEntryCompleted. A cached World avatar/ObjectId is not session proof.
        if client_process is not None and client_process.poll() is not None:
            raise ValueError('The sandbox client closed before entry. Inspect profile/ArcheAge.log on E.')
        if presentation is not None and getattr(presentation, '_error', None):
            raise ValueError(f'Sandbox presentation failed: {presentation._error}')
        return character_ready(root)
    entered = False
    try:
        wait_for(character_entered, 'Automatic character entry', seconds=360)
        entered = True
        print('Entrada automática completada. Preparando los objetivos del escenario...', flush=True)
        # Entry completion can lag the online registry while the real map loads.
        wait_for(lambda: command(root, 'begin'), 'Sandbox preparation')
        result = wait_for(lambda: ready_result(root), 'Scenario ready')
    except BaseException as error:
        if presentation:
            if entered:
                # A development-scene error must not throw away the connected client.
                try:
                    presentation.reveal()
                except Exception as panel_error:
                    capture(root, 'panel-close-after-scene-error', {'error': str(panel_error)})
                capture(root, 'scene-preparation-failed-session-kept',
                        {'pid': client_process.pid, 'error': str(error), 'characterId': CHARACTER_ID})
                print('El personaje sigue conectado. La preparación falló; se conserva el cliente para corregir en caliente.', flush=True)
            else:
                presentation.cancel()
        raise
    if presentation:
        capture(root, 'presentation-ready', {'pid': client_process.pid, 'readyAtUtc': timestamp(),
                                             'attempt': result.get('attempt'),
                                             'dummyCount': len(result.get('dummies', []))})
        try:
            presentation.reveal()
        except BaseException:
            presentation.cancel()
            raise
    capture(root, 'begin', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def character_ready(root):
    value = api(root, '/api/mechanics-sandbox/status', {'character': CHARACTER_NAME})
    return value.get('characterId') == CHARACTER_ID and value.get('state') not in ('offline', 'rejected')


def ready_result(root):
    result = command(root, 'status')
    if result.get('state') == 'faulted':
        raise ValueError(result.get('message', 'Sandbox reset faulted'))
    return result if result.get('state') == 'ready' else None


def idle_result(root):
    result = command(root, 'status')
    return result if result.get('state') == 'idle' else None


def capture(root, action, value):
    write_json(root/'captures'/f'{timestamp()}-{action}.json', value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'seed', 'build', 'start', 'watch', 'tool', 'status', 'reset', 'clear', 'panel-check', 'hub'])
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--start-zone', action='store_true', help='Authorize only the installed active sandbox Zone profile')
    parser.add_argument('--no-client', action='store_true')
    parser.add_argument('--visible-client', action='store_true', help='Diagnostic: normal visible rendering during boot')
    args = parser.parse_args()
    root = safe_root(args.root)
    os.environ.update(execution_env(root))
    if args.action == 'prepare':
        print(json.dumps(prepare(root), ensure_ascii=False, indent=2))
    elif args.action == 'seed':
        prepare(root)
        seed(root)
    elif args.action == 'build':
        prepare(root)
        compose(root, 'build', 'game', stdout=None)
        print('Imagen del sandbox compilada.')
    elif args.action == 'watch':
        from aa10_sandbox_watch import prepare as prepare_watch
        prepare_watch(root)
        start(root, args.start_zone, args.no_client, args.visible_client)
    elif args.action == 'tool':
        from contextlib import redirect_stdout, redirect_stderr
        from aa10_sandbox_tool import show
        (root/'logs').mkdir(parents=True, exist_ok=True)
        with (root/'logs/development-tool.log').open('a', encoding='utf-8', buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                show(root)
    elif args.action == 'start':
        start(root, args.start_zone, args.no_client, args.visible_client)
    elif args.action == 'status':
        print(json.dumps(api(root, '/api/world/zone-manager-status'), ensure_ascii=False, indent=2))
    elif args.action == 'panel-check':
        from aa10_sandbox_panel_check import check
        check(root)
    elif args.action == 'hub':
        from aa10_sandbox_hub import apply
        print(json.dumps(apply(root), ensure_ascii=False, indent=2))
    else:
        result = command(root, args.action)
        if args.action == 'reset':
            result = wait_for(lambda: ready_result(root), 'Scenario reset')
        elif args.action == 'clear':
            result = wait_for(lambda: idle_result(root), 'Scenario cleanup')
        capture(root, args.action, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, TimeoutError, OSError) as error:
        write_json(DEFAULT_ROOT/'logs/last-launch-error.json', {'atUtc': timestamp(), 'error': str(error)})
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
