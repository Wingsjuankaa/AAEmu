[CmdletBinding()]
param(
    [string]$GamePak = 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak',
    [string]$WorldConfig = 'E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Configurations\World.json',
    [string]$RetailDatabase = 'E:\AAEmu\rama_10\data\sqlite\retail\compact.sqlite3',
    [string]$BackupRoot = 'E:\AAEmu\rama_10\backups\client-patches',
    [switch]$Apply,
    [switch]$SkipFullPakHash
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gamePakPath = (Resolve-Path -LiteralPath $GamePak).Path
$worldConfigPath = (Resolve-Path -LiteralPath $WorldConfig).Path
$retailDatabasePath = (Resolve-Path -LiteralPath $RetailDatabase).Path
$extractProject = Join-Path $repo 'reconstruccion_cliente_10\tools\PakEntryExtract\PakEntryExtract.csproj'
$replaceProject = Join-Path $repo 'Tools\PakEntryReplace\PakEntryReplace.csproj'
$synchronizer = Join-Path $repo 'Scripts\SyncAa10GrowthRateTooltip.py'
$entryName = 'game/db/compact.sqlite3'
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-growth-rate-tooltip-$timestamp"

if ($Apply -and (Get-Process -Name archeage -ErrorAction SilentlyContinue)) {
    throw 'Close archeage.exe before applying the game_pak growth-rate patch.'
}
if (Test-Path -LiteralPath $patchRoot) {
    throw "Refusing to reuse patch directory: $patchRoot"
}
New-Item -ItemType Directory -Path $patchRoot | Out-Null

$before = Join-Path $patchRoot 'compact.before.sqlite3'
$replacement = Join-Path $patchRoot 'compact.replacement.sqlite3'
$verified = Join-Path $patchRoot 'compact.verified.sqlite3'

function Invoke-Checked {
    param([scriptblock]$Command, [string]$Description)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Export-Compact([string]$Output) {
    Invoke-Checked {
        dotnet run --project $extractProject --configuration Release -- `
            $gamePakPath $entryName $Output
    } "Extracting $entryName"
}

$packageSizeBefore = (Get-Item -LiteralPath $gamePakPath).Length
$packageHashBefore = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }

Export-Compact $before
$entryHashBefore = Get-Sha256 $before
$entrySize = (Get-Item -LiteralPath $before).Length
Copy-Item -LiteralPath $before -Destination $replacement

Invoke-Checked {
    python $synchronizer `
        --world-config $worldConfigPath `
        --retail-database $retailDatabasePath `
        --client-database $replacement `
        --apply `
        --preserve-size
} 'Building size-preserving growth-rate compact'

if ((Get-Item -LiteralPath $replacement).Length -ne $entrySize) {
    throw 'Generated compact does not preserve the PAK entry size.'
}
$replacementHash = Get-Sha256 $replacement
$changed = $false

try {
    if ($Apply) {
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $replacement $entryHashBefore
        } "Replacing $entryName"
        $changed = $replacementHash -ne $entryHashBefore
    }

    if ($Apply) {
        Export-Compact $verified
        $verifiedHash = Get-Sha256 $verified
        if ($verifiedHash -ne $replacementHash) {
            throw "Post-operation hash mismatch: $verifiedHash != $replacementHash"
        }
    }
    else {
        $verifiedHash = $entryHashBefore
    }
}
catch {
    if ($Apply -and $changed) {
        Write-Warning 'Patch failed; restoring the original compact entry.'
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $before $replacementHash
        } "Rolling back $entryName"
    }
    throw
}

$packageSizeAfter = (Get-Item -LiteralPath $gamePakPath).Length
if ($packageSizeAfter -ne $packageSizeBefore) {
    throw "game_pak size changed: $packageSizeBefore -> $packageSizeAfter"
}
$packageHashAfter = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }
$rate = (Get-Content -LiteralPath $worldConfigPath -Raw | ConvertFrom-Json).World.GrowthRate
$manifest = [ordered]@{
    schemaVersion = 1
    patchId = 'aa10-growth-rate-tooltip-r575'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = (git -C $repo rev-parse HEAD).Trim()
    applied = [bool]$Apply
    growthRate = $rate
    gamePak = [ordered]@{
        path = $gamePakPath
        sizeBefore = $packageSizeBefore
        sizeAfter = $packageSizeAfter
        sha256Before = $packageHashBefore
        sha256After = $packageHashAfter
    }
    entry = [ordered]@{
        name = $entryName
        size = $entrySize
        sha256Before = $entryHashBefore
        sha256Replacement = $replacementHash
        sha256Verified = $verifiedHash
        rollbackFile = $before
        replacementFile = $replacement
    }
}
$manifestPath = Join-Path $patchRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Patch mode: $($(if ($Apply) { 'APPLIED' } else { 'DRY RUN' }))"
Write-Host "GrowthRate: $rate"
Write-Host "Entry SHA-256: $entryHashBefore -> $replacementHash"
Write-Host "Rollback and manifest: $patchRoot"
