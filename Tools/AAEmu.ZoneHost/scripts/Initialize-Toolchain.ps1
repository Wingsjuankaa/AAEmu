[CmdletBinding()]
param([string]$ToolchainRoot = 'E:\AAEmu\rama_10\artifacts\toolchains\zonehost-rust')
$ErrorActionPreference = 'Stop'
$settings = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../build-settings.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $ToolchainRoot -Force | Out-Null
$env:RUSTUP_HOME = Join-Path $ToolchainRoot 'rustup'
$env:CARGO_HOME = Join-Path $ToolchainRoot 'cargo'
$rustup = Join-Path $env:CARGO_HOME 'bin/rustup.exe'
if (-not (Test-Path -LiteralPath $rustup)) {
    $installer = Join-Path $ToolchainRoot 'rustup-init.exe'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe' -OutFile $installer
    $installerHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
    # Identifies the bootstrap reviewed with this integration; fail on upstream replacement.
    if ($installerHash -ne '6F4BEF66261261FCB43131BE8720BAB817D403A09EDEC7455C371974B90BDB7E') {
        throw 'rustup-init changed. Review and update its pinned SHA-256 before executing it.'
    }
    & $installer -y --no-modify-path --profile minimal --default-host $settings.target --default-toolchain $settings.rustToolchain
} else {
    & $rustup toolchain install $settings.rustToolchain --profile minimal
}
if ($LASTEXITCODE -ne 0) { throw 'Rust toolchain installation failed.' }
Write-Output "Isolated Rust toolchain ready: $ToolchainRoot (global PATH unchanged)."
