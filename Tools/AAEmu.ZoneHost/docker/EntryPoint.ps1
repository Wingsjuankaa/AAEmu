[CmdletBinding()]
param([ValidateSet('Probe', 'Run')][string]$Mode = 'Probe')
$ErrorActionPreference = 'Stop'
if ($Mode -eq 'Probe') {
    & 'C:\app\Test-Candidate.ps1' -Bundle 'C:\app'
    exit 0
}
# Run mode is an explicit operator experiment on ONE isolated runtime, never automatic.
foreach ($name in @('AA10_ZONE_NAME', 'AA10_WORLD_IP')) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Required environment variable: $name" }
}
if ($env:AA10_ZONE_NAME -notmatch '^[a-z0-9_]+$') { throw 'Invalid zone resource name.' }
if (-not (Test-Path -LiteralPath 'C:\AA\.aaemu-zonehost-isolated-runtime' -PathType Leaf)) {
    throw 'Mount an isolated, writable Zone runtime at C:\AA with the required marker. Never mount the active runtime.'
}
foreach ($file in @('C:\AA\Bin64\x2game-dev_dedicate.dll','C:\AA\Bin64\CrySystem.dll',
    'C:\AA\Bin64\msvcr100.dll','C:\AA\Bin64\msvcp100.dll','C:\AA\game_pak',
    'C:\AA\game\db\game_decrypted.sqlite3')) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing runtime input: $file" }
}
$manifest = Get-Content -LiteralPath 'C:\app\build-manifest.json' -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath 'C:\app\AAEmu.ZoneHost.exe').Hash -ne $manifest.binarySha256) { throw 'Image binary differs from build manifest.' }
Copy-Item -LiteralPath 'C:\app\AAEmu.ZoneHost.exe' -Destination 'C:\AA\Bin64\AAEmu.ZoneHost.exe' -Force
$audit = (& 'C:\app\Test-NativeRuntime.ps1' -BinDirectory 'C:\AA\Bin64') | ConvertFrom-Json
if (-not $audit.matchesUnpatchedShipSitesAndConsoleExport) { throw 'Native static compatibility checks failed.' }
$env:AAEMU_ZONE_DLL = 'C:\AA\Bin64\x2game-dev_dedicate.dll'
$env:AAEMU_ZONE_SAVE_DIR = 'C:\zone-save'
$env:AAEMU_ZONE_LOG_NAME = "zone-$($env:AA10_ZONE_NAME).log"
New-Item -ItemType Directory -Path $env:AAEMU_ZONE_SAVE_DIR -Force | Out-Null
$port = 1240
if ($env:AA10_WORLD_PORT) { $port = [int]$env:AA10_WORLD_PORT }
if ($port -lt 1 -or $port -gt 65535) { throw 'Invalid World port.' }
Set-Location -LiteralPath 'C:\AA\Bin64'
& '.\AAEmu.ZoneHost.exe' -dedicated +zone $env:AA10_ZONE_NAME +sv_map $env:AA10_ZONE_NAME `
    +world_ip $env:AA10_WORLD_IP +world_port $port +world_serveraddr $env:AA10_WORLD_IP +world_serverport $port `
    +db_location game/db/game_decrypted.sqlite3 +sys_dedicated_server 1 +e_render 0 +r_Driver Null
exit $LASTEXITCODE
