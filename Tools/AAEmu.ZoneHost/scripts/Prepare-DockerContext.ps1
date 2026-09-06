[CmdletBinding()]
param(
    [string]$Bundle = 'E:\AAEmu\rama_10\artifacts\builds\zonehost\release',
    [string]$Destination = 'E:\AAEmu\rama_10\artifacts\builds\zonehost\docker-context'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath $Destination) {
    if (@(Get-ChildItem -LiteralPath $Destination -Force).Count -gt 0) {
        throw 'Choose a new or empty context directory; no existing files will be replaced.'
    }
}
& (Join-Path $PSScriptRoot 'Test-Candidate.ps1') -Bundle $Bundle
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
foreach ($name in @('AAEmu.ZoneHost.exe','build-manifest.json')) {
    Copy-Item -LiteralPath (Join-Path $Bundle $name) -Destination (Join-Path $Destination $name)
}
Copy-Item -LiteralPath (Join-Path $root 'upstream/LICENSE') -Destination (Join-Path $Destination 'LICENSE')
Copy-Item -LiteralPath (Join-Path $root 'docker/Dockerfile.windows.experimental') -Destination (Join-Path $Destination 'Dockerfile')
Copy-Item -LiteralPath (Join-Path $root 'docker/EntryPoint.ps1') -Destination (Join-Path $Destination 'EntryPoint.ps1')
foreach ($name in @('Test-Candidate.ps1','Test-NativeRuntime.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $Destination $name)
}
@('**', '!Dockerfile', '!AAEmu.ZoneHost.exe', '!build-manifest.json', '!LICENSE', '!EntryPoint.ps1', '!Test-Candidate.ps1', '!Test-NativeRuntime.ps1') |
    Set-Content -LiteralPath (Join-Path $Destination '.dockerignore') -Encoding ascii
Write-Output "Prepared context without retail DLLs, databases or game_pak: $Destination"
Write-Output 'Not built or started. A compatible Windows container engine is required.'
