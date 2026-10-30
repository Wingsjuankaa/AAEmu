"""Check the real isolated Tk process exit without reopening or covering the running game."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import aa10_sandbox as sandbox


def check(root):
    executable = root/'client/Bin64/archeage.exe'
    target = str(executable).replace("'", "''")
    script = (f"$target='{target}'; $p=@(Get-CimInstance Win32_Process -Filter \"Name='archeage.exe'\" | "
              "Where-Object {$_.ExecutablePath -eq $target}); "
              "@{processes=@($p | Select-Object ProcessId,CreationDate); "
              "sockets=@(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
              "Where-Object {$_.OwningProcess -in $p.ProcessId -and $_.RemotePort -in 3239,3250} | "
              "Select-Object OwningProcess,LocalPort,RemotePort)} | ConvertTo-Json -Depth 4 -Compress")
    snapshot = lambda: json.loads(sandbox.run(['powershell.exe', '-NoProfile', '-Command', script], root=root).stdout)
    before = snapshot()
    if len(before['processes']) != 1 or len(before['sockets']) != 2:
        raise RuntimeError('Mantén abierto y conectado el cliente del sandbox para esta comprobación.')
    directory = Path(tempfile.mkdtemp(prefix='panel-exit-check-', dir=root/'temp'))
    ready, error = directory/'ready.signal', directory/'error.json'
    # Ready BEFORE creating Tk: its window remains withdrawn throughout the check.
    ready.write_text('ready', encoding='ascii')
    args = [str(Path(sys.executable).with_name('pythonw.exe')), '-B',
            str(sandbox.REPO/'Scripts/aa10_sandbox_window.py'), '--game-pid',
            str(before['processes'][0]['ProcessId']), '--ready', str(ready), '--error', str(error),
            '--executable', str(executable)]
    process = subprocess.run(args, env=sandbox.execution_env(root), cwd=directory,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    if process.returncode or error.exists():
        detail = json.loads(error.read_text(encoding='utf-8'))['error'] if error.exists() else str(process.returncode)
        raise RuntimeError('El panel no terminó limpiamente: '+detail)
    after = snapshot()
    sockets = lambda value: sorted((item['LocalPort'], item['RemotePort']) for item in value['sockets'])
    if before['processes'] != after['processes'] or sockets(before) != sockets(after):
        raise RuntimeError('La conexión del juego cambió durante la comprobación.')
    result = {'success': True, 'atUtc': sandbox.timestamp(), 'helperExitCode': process.returncode,
              'clientPid': before['processes'][0]['ProcessId'], 'sameNetworkSession': True,
              'panelWasShown': False, 'stateDirectory': str(directory)}
    sandbox.capture(root, 'panel-helper-exit', result)
    print('OK: panel cerrado sin error; el cliente y sus conexiones siguen iguales.')
    return result
