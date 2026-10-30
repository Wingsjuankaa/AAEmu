[CmdletBinding()]
param(
    [ValidateSet('start', 'watch', 'tool', 'prepare', 'seed', 'build', 'status', 'reset', 'clear', 'panel-check', 'hub')]
    [string]$Action = 'start',
    [switch]$StartZone,
    [switch]$NoClient,
    [switch]$VisibleClient
)
$ErrorActionPreference = 'Stop'
$projectRoot = 'E:\AAEmu\rama_10'
$runtimeRoot = Join-Path $projectRoot 'runtime\sandbox-aa10'
$env:TEMP = Join-Path $runtimeRoot 'temp'
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$runnerArguments = @('-B', (Join-Path $PSScriptRoot 'aa10_sandbox.py'), $Action)
if ($StartZone) { $runnerArguments += '--start-zone' }
if ($NoClient) { $runnerArguments += '--no-client' }
if ($VisibleClient) { $runnerArguments += '--visible-client' }
$launcherLogDirectory = Join-Path $runtimeRoot 'logs'
New-Item -ItemType Directory -Force -Path $launcherLogDirectory | Out-Null
$launcherLog = Join-Path $launcherLogDirectory ('launcher-' + $Action + '.log')
$ErrorActionPreference = 'Continue'
& python @runnerArguments 2>&1 | Tee-Object -FilePath $launcherLog
$sandboxExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($sandboxExitCode -ne 0) { throw "AA10 sandbox failed ($sandboxExitCode). Log: $launcherLog" }
