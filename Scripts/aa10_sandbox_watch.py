"""Run actual AAEmu.World/Game sources with SDK Hot Reload in the isolated stack."""
import copy
import aa10_sandbox as sandbox


def prepare(root):
    profile = sandbox.prepare(root)
    value = copy.deepcopy(sandbox.read_jsonc(root/'compose.json'))
    game = value['services']['game']
    game.pop('build', None)
    game['image'] = 'mcr.microsoft.com/dotnet/sdk:10.0-alpine'
    game['working_dir'] = '/src'
    game['entrypoint'] = ['dotnet', 'watch', '--project',
                         '/src/AAEmu.WorldServer/AAEmu.World/AAEmu.World.csproj',
                         '--configuration', 'Debug', '--no-launch-profile', '--non-interactive', '--verbose',
                         '--artifacts-path', '/runtime/watch-build']
    game['command'] = []
    # CLR named mutexes and Hot Reload IPC require Unix sockets/locks, unavailable
    # on a Windows bind mount. RAM-only /tmp leaves no host-drive residue.
    game['tmpfs'] = ['/tmp:rw,nosuid,nodev,size=512m,mode=1777',
                     '/run/aa10:rw,nosuid,nodev,size=64m,mode=700']
    game['environment'].update({
        'GameContentRoot': '/app/game', 'ZoneGameDataRoot': '/app/game/ClientData/game',
        'PublicNetwork__Host': '127.0.0.1', 'PublicNetwork__Port': '3239',
        'ZoneHost__Enabled': 'false', 'HOME': '/runtime/dotnet-home',
        'DOTNET_CLI_HOME': '/runtime/dotnet-home', 'NUGET_PACKAGES': '/cache/packages',
        'TMPDIR': '/tmp', 'XDG_RUNTIME_DIR': '/run/aa10', 'XDG_CACHE_HOME': '/runtime/cache',
        'DOTNET_BUNDLE_EXTRACT_BASE_DIR': '/runtime/bundle-extract',
        'DOTNET_CLI_TELEMETRY_OPTOUT': '1', 'DOTNET_GENERATE_ASPNET_CERTIFICATE': 'false',
        'DOTNET_ADD_GLOBAL_TOOLS_TO_PATH': 'false', 'DOTNET_WATCH_SUPPRESS_LAUNCH_BROWSER': '1',
        'DOTNET_WATCH_SUPPRESS_EMOJIS': '1', 'DOTNET_USE_POLLING_FILE_WATCHER': '1'
    })
    bind = lambda source, target, readonly=False: {
        'type': 'bind', 'source': str(source).replace('\\', '/'), 'target': target, 'read_only': readonly}
    nlog = root/'config/NLog.game.config'
    if not nlog.exists():
        nlog.write_bytes((sandbox.REPO/'AAEmu.Game/NLog.config').read_bytes())
    game['volumes'].extend([bind(sandbox.REPO, '/src'), bind(root, '/runtime'),
                            bind(sandbox.PROJECT/'artifacts/cache/nuget', '/cache/packages'),
                            bind(nlog, '/app/game/NLog.config', True)])
    for relative in ['Scripts', 'Configs']:
        source = sandbox.REPO/'AAEmu.Game'/relative
        if source.exists():
            game['volumes'].append(bind(source, '/app/game/'+relative, True))
    config = sandbox.read_jsonc(root/'config/Game.json')
    config['WebApiNetwork']['Host'] = '127.0.0.1'
    config['DebugInfo'] = False
    sandbox.write_json(root/'config/Game.json', config)
    sandbox.write_json(root/'compose.watch.json', value)
    sandbox.write_json(root/'watch-mode.json', {
        'schema': 1, 'mode': 'real-source-sdk-watch',
        'project': 'AAEmu.WorldServer/AAEmu.World/AAEmu.World.csproj',
        'source': str(sandbox.REPO), 'artifacts': str(root/'watch-build'),
        'supportedEdits': 'Supported C# edits reload live; rude edits require a process restart',
    })
    return profile
