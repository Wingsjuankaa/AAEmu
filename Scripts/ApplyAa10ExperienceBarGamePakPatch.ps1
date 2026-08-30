[CmdletBinding()]
param(
    [string]$GamePak = 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak',
    [string]$Luac = 'E:\AAEmu-Research\work\lua-5.1.5-msvc\lua-5.1.5\src\luac51.exe',
    [string]$BackupRoot = 'E:\AAEmu\rama_10\backups\client-patches',
    [switch]$Apply,
    [switch]$SkipFullPakHash
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gamePakPath = (Resolve-Path -LiteralPath $GamePak).Path
$luacPath = (Resolve-Path -LiteralPath $Luac).Path
$extractProject = Join-Path $repo 'reconstruccion_cliente_10\tools\PakEntryExtract\PakEntryExtract.csproj'
$replaceProject = Join-Path $repo 'Tools\PakEntryReplace\PakEntryReplace.csproj'
$builder = Join-Path $repo 'Scripts\PatchAa10ExperienceBar.py'
$entryName = 'game/scriptsbin64/x2ui/hud/main_menu_bar/exp_bar_set.alb'
$sourceEntryName = 'game/scripts/x2ui/hud/main_menu_bar/exp_bar_set.lua'
$originalHash = '3831551627119BA57E5B7D360D834EAD2F835D19665DF207CFA89B880B15E6D1'
$patchedHash = '2E53830616C656D666C29C2EA39A56AD4C21BCE1A9ED024A935572AA7CEE41F5'
$sourceHash = 'A80E862583E2DF20AADA0F81386B24379154D04CE335216CB8BC1D85D5786ECC'
$entrySize = 16807
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-experience-bar-$timestamp"

if (Test-Path -LiteralPath $patchRoot) {
    throw "Refusing to reuse patch directory: $patchRoot"
}
New-Item -ItemType Directory -Path $patchRoot | Out-Null

$before = Join-Path $patchRoot 'exp_bar_set.before.alb'
$source = Join-Path $patchRoot 'exp_bar_set.lua'
$replacement = Join-Path $patchRoot 'exp_bar_set.replacement.alb'
$verified = Join-Path $patchRoot 'exp_bar_set.verified.alb'

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

function Export-PakEntry([string]$Entry, [string]$Output) {
    Invoke-Checked {
        dotnet run --project $extractProject --configuration Release -- $gamePakPath $Entry $Output
    } "Extracting $Entry"
}

$packageSizeBefore = (Get-Item -LiteralPath $gamePakPath).Length
$packageHashBefore = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }

Export-PakEntry $entryName $before
Export-PakEntry $sourceEntryName $source
$entryHashBefore = Get-Sha256 $before
$sourceHashBefore = Get-Sha256 $source
if ($sourceHashBefore -ne $sourceHash) {
    throw "Unexpected $sourceEntryName SHA-256 $sourceHashBefore"
}
if ((Get-Item -LiteralPath $before).Length -ne $entrySize) {
    throw "Unexpected $entryName size"
}
if ($entryHashBefore -ne $originalHash -and $entryHashBefore -ne $patchedHash) {
    throw "Unexpected $entryName SHA-256 $entryHashBefore"
}
if ($Apply -and $entryHashBefore -eq $originalHash -and (Get-Process -Name archeage -ErrorAction SilentlyContinue)) {
    throw 'Close archeage.exe before applying the experience-bar game_pak patch.'
}

Invoke-Checked {
    python -B $builder --source $source --alb $before --luac $luacPath --output $replacement
} 'Building the AA10 ancestral experience-bar replacement'

if ((Get-Item -LiteralPath $replacement).Length -ne $entrySize) {
    throw 'Generated replacement does not preserve the PAK entry size.'
}
if ((Get-Sha256 $replacement) -ne $patchedHash) {
    throw 'Generated replacement hash is not deterministic.'
}

$changed = $false
try {
    if ($Apply -and $entryHashBefore -eq $originalHash) {
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $replacement $originalHash
        } "Replacing $entryName"
        $changed = $true
    }

    if ($Apply) {
        Export-PakEntry $entryName $verified
        $verifiedHash = Get-Sha256 $verified
        if ($verifiedHash -ne $patchedHash) {
            throw "Post-operation verification failed: $verifiedHash"
        }
    }
    else {
        Copy-Item -LiteralPath $before -Destination $verified
        $verifiedHash = $entryHashBefore
    }
}
catch {
    if ($Apply -and $changed) {
        Write-Warning 'Patch failed; restoring the entry changed by this invocation.'
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $before $patchedHash
        } "Rolling back $entryName"
    }
    throw
}

$packageSizeAfter = (Get-Item -LiteralPath $gamePakPath).Length
if ($packageSizeAfter -ne $packageSizeBefore) {
    throw "game_pak size changed: $packageSizeBefore -> $packageSizeAfter"
}
$packageHashAfter = if ($SkipFullPakHash) {
    $null
}
elseif (-not $changed) {
    # No package bytes changed during this idempotent invocation.
    $packageHashBefore
}
else {
    Get-Sha256 $gamePakPath
}
$manifest = [ordered]@{
    schemaVersion = 1
    patchId = 'aa10-ancestral-experience-bar-r575'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = (git -C $repo rev-parse HEAD).Trim()
    applied = [bool]$Apply
    alreadyPatched = $entryHashBefore -eq $patchedHash
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
        sha256ExpectedOriginal = $originalHash
        sha256ExpectedPatched = $patchedHash
        sha256Verified = $verifiedHash
        rollbackFile = $before
        replacementFile = $replacement
        sourceEntry = $sourceEntryName
        sourceFile = $source
        sourceSha256 = $sourceHashBefore
    }
}
$manifestPath = Join-Path $patchRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Patch mode: $($(if ($Apply) { 'APPLIED' } else { 'DRY RUN' }))"
Write-Host "Entry SHA-256: $entryHashBefore -> $patchedHash"
Write-Host "Rollback and manifest: $patchRoot"
Write-Host "Manifest: $manifestPath"
