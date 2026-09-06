[CmdletBinding()]
param(
    [string]$ToolchainRoot = 'E:\AAEmu\rama_10\artifacts\toolchains\zonehost-rust',
    [string]$OutputRoot = 'E:\AAEmu\rama_10\artifacts\builds\zonehost',
    [ValidateSet('Release', 'Debug')][string]$Configuration = 'Release',
    [string]$RuntimeBinDirectory = 'E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64',
    [switch]$NoPublish
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$settings = Get-Content -LiteralPath (Join-Path $root 'build-settings.json') -Raw | ConvertFrom-Json
& (Join-Path $PSScriptRoot 'Test-UpstreamSnapshot.ps1')
$env:RUSTUP_HOME = Join-Path $ToolchainRoot 'rustup'
$env:CARGO_HOME = Join-Path $ToolchainRoot 'cargo'
$cargo = Join-Path $env:CARGO_HOME 'bin/cargo.exe'
$rustc = Join-Path $env:CARGO_HOME 'bin/rustc.exe'
if (-not (Test-Path -LiteralPath $cargo)) { throw 'Run scripts/Initialize-Toolchain.ps1 first.' }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Visual Studio Installer/vswhere.exe not found.' }
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Install Visual Studio C++ x64 build tools and a Windows SDK.' }
Import-Module (Join-Path $vs 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $vs -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
$env:CARGO_TARGET_DIR = Join-Path $OutputRoot 'cargo'
$env:SOURCE_DATE_EPOCH = $settings.sourceDateEpoch
$env:RUSTFLAGS = '--remap-path-prefix="' + $root + '=/aaemu-zonehost" -C link-arg=/Brepro -C target-feature=+crt-static'
$arguments = @("+$($settings.rustToolchain)", 'build', '--frozen', '--offline', '--target', $settings.target,
    '--manifest-path', (Join-Path $root 'upstream/AAEmu.ZoneHost.Native/Cargo.toml'))
if ($Configuration -eq 'Release') { $arguments += '--release' }
& $cargo @arguments
if ($LASTEXITCODE -ne 0) { throw 'ZoneHost compilation failed.' }
$profile = $Configuration.ToLowerInvariant()
$sourceExe = Join-Path $env:CARGO_TARGET_DIR "$($settings.target)/$profile/aaemu-zone-host.exe"
$bundle = Join-Path $OutputRoot $profile
New-Item -ItemType Directory -Path $bundle -Force | Out-Null
$binary = Join-Path $bundle 'AAEmu.ZoneHost.exe'
Copy-Item -LiteralPath $sourceExe -Destination $binary -Force
$compiler = @(& $rustc "+$($settings.rustToolchain)" -Vv)
$cargoVersion = & $cargo "+$($settings.rustToolchain)" -V
$sourceManifest = Get-Content -LiteralPath (Join-Path $root 'upstream-manifest.json') -Raw | ConvertFrom-Json
if ($sourceManifest.commit -ne $settings.upstreamCommit) { throw 'Build settings and source commit differ.' }
$record = [ordered]@{
    schemaVersion = 1
    builtAtUtc = [DateTime]::UtcNow.ToString('o')
    upstreamRepository = $sourceManifest.repository
    upstreamCommit = $sourceManifest.commit
    sourceManifestSha256 = (Get-FileHash -LiteralPath (Join-Path $root 'upstream-manifest.json')).Hash
    buildSettingsSha256 = (Get-FileHash -LiteralPath (Join-Path $root 'build-settings.json')).Hash
    buildScriptSha256 = (Get-FileHash -LiteralPath $PSCommandPath).Hash
    rustc = $compiler
    cargo = $cargoVersion
    visualStudio = $vs
    msvcVersion = $env:VCToolsVersion
    windowsSdkVersion = $env:WindowsSDKVersion
    rustFlags = $env:RUSTFLAGS
    configuration = $Configuration
    binarySha256 = (Get-FileHash -LiteralPath $binary).Hash
    binaryBytes = (Get-Item -LiteralPath $binary).Length
    shipPhysicalizationPatch = 'upstream always applies or verifies the patch in memory before CreateGameStartup'
    runtimeAcceptance = 'not performed by build; no Zone is launched'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $bundle 'build-manifest.json') -Encoding utf8
Write-Output "Built candidate: $binary"
Write-Output "SHA256: $($record.binarySha256)"
& (Join-Path $PSScriptRoot 'Test-Candidate.ps1') -Bundle $bundle
if ($Configuration -eq 'Release' -and -not $NoPublish) {
    $audit = (& (Join-Path $PSScriptRoot 'Test-NativeRuntime.ps1') -BinDirectory $RuntimeBinDirectory) | ConvertFrom-Json
    if (-not $audit.matchesUnpatchedShipSitesAndConsoleExport) { throw 'Runtime compatibility check failed; candidate built but not published.' }
    & (Join-Path $PSScriptRoot 'Publish-ZoneHost.ps1') -Bundle $bundle -BinDirectory $RuntimeBinDirectory
} else {
    Write-Output 'Build only: Control Center runtime not updated (Debug or -NoPublish).'
}
