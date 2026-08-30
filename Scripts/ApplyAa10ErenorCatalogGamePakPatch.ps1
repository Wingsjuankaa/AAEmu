[CmdletBinding()]
param(
    [string]$GamePak = 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak',
    [string]$ClientLooseDatabase = 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3',
    [string]$RuntimeDatabase = 'E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Data\compact.sqlite3',
    [string]$BackupRoot = 'E:\AAEmu\rama_10\backups\client-patches',
    [switch]$Apply,
    [switch]$SkipFullPakHash
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gamePakPath = (Resolve-Path -LiteralPath $GamePak).Path
$clientLoosePath = (Resolve-Path -LiteralPath $ClientLooseDatabase).Path
$runtimePath = (Resolve-Path -LiteralPath $RuntimeDatabase).Path
$extractProject = Join-Path $repo 'reconstruccion_cliente_10\tools\PakEntryExtract\PakEntryExtract.csproj'
$replaceProject = Join-Path $repo 'Tools\PakEntryReplace\PakEntryReplace.csproj'
$builder = Join-Path $repo 'Scripts\PatchAa10ErenorCatalog.py'
$entryName = 'game/db/compact.sqlite3'
$probeEntries = @(
    'game/ui/icon/icon_item_shotgun_0024.dds',
    'game/objects/characters/animals/buffalo/buffalo.cgf'
)

$profiles = @{
    embedded = @{
        '7472265C95AB20E1E13D9BBD696258E25704C67D405DEF249784FBFA0AD50C74' = @{ size = 440823808L; after = 'FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5'; afterSize = 440823808L }
        'FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5' = @{ size = 440823808L; after = 'FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5'; afterSize = 440823808L }
    }
    loose = @{
        'F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75' = @{ size = 440832000L; after = 'F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B'; afterSize = 440836096L }
        'F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B' = @{ size = 440836096L; after = 'F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B'; afterSize = 440836096L }
    }
    runtime = @{
        '1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D' = @{ size = 552178688L; after = '85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65'; afterSize = 552178688L }
        '85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65' = @{ size = 552178688L; after = '85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65'; afterSize = 552178688L }
    }
}

$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-erenor-catalog-$timestamp"
if (Test-Path -LiteralPath $patchRoot) {
    throw "Refusing to reuse patch directory: $patchRoot"
}
New-Item -ItemType Directory -Path $patchRoot | Out-Null

$entryBefore = Join-Path $patchRoot 'compact.pak.before.sqlite3'
$entryReplacement = Join-Path $patchRoot 'compact.pak.replacement.sqlite3'
$entryVerified = Join-Path $patchRoot 'compact.pak.verified.sqlite3'
$clientBefore = Join-Path $patchRoot 'compact.client-loose.before.sqlite3'
$clientReplacement = Join-Path $patchRoot 'compact.client-loose.replacement.sqlite3'
$runtimeBefore = Join-Path $patchRoot 'compact.runtime.before.sqlite3'
$runtimeReplacement = Join-Path $patchRoot 'compact.runtime.replacement.sqlite3'

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

function Export-PakEntry([string]$Name, [string]$Output) {
    Invoke-Checked {
        dotnet run --project $extractProject --configuration Release -- `
            $gamePakPath $Name $Output
    } "Extracting $Name"
}

function Resolve-Profile {
    param([string]$Path, [hashtable]$Known, [string]$Label)
    $hash = Get-Sha256 $Path
    if (-not $Known.ContainsKey($hash)) {
        throw "$Label has unknown SHA-256 $hash"
    }
    $profile = $Known[$hash]
    $size = (Get-Item -LiteralPath $Path).Length
    if ($size -ne $profile.size) {
        throw "$Label has unexpected size $size (expected $($profile.size))"
    }
    return [pscustomobject]@{
        hash = $hash
        size = $size
        expectedHash = $profile.after
        expectedSize = $profile.afterSize
    }
}

function Build-Replacement {
    param([string]$Source, [string]$Output, [pscustomobject]$Profile, [string]$Label)
    Copy-Item -LiteralPath $Source -Destination $Output
    $arguments = @('-B', $builder, '--apply', '--json', $Output)
    if ($Profile.expectedSize -eq $Profile.size) {
        $arguments += '--preserve-size'
    }
    Invoke-Checked { python @arguments } "Building $Label"
    $actualSize = (Get-Item -LiteralPath $Output).Length
    $actualHash = Get-Sha256 $Output
    if ($actualSize -ne $Profile.expectedSize -or $actualHash -ne $Profile.expectedHash) {
        throw "$Label replacement identity mismatch: $actualSize/$actualHash"
    }
}

if ($Apply -and (Get-Process -Name archeage -ErrorAction SilentlyContinue)) {
    throw 'Close archeage.exe before applying the Erenor catalog patch.'
}

$packageSizeBefore = (Get-Item -LiteralPath $gamePakPath).Length
$packageHashBefore = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }
Export-PakEntry $entryName $entryBefore
Copy-Item -LiteralPath $clientLoosePath -Destination $clientBefore
Copy-Item -LiteralPath $runtimePath -Destination $runtimeBefore

$embeddedProfile = Resolve-Profile $entryBefore $profiles.embedded 'embedded compact'
$looseProfile = Resolve-Profile $clientBefore $profiles.loose 'loose compact'
$runtimeProfile = Resolve-Profile $runtimeBefore $profiles.runtime 'runtime compact'

$probeBefore = @{}
for ($index = 0; $index -lt $probeEntries.Count; $index++) {
    $path = Join-Path $patchRoot "probe-$index.before"
    Export-PakEntry $probeEntries[$index] $path
    $probeBefore[$probeEntries[$index]] = @{ path = $path; hash = Get-Sha256 $path }
}

Build-Replacement $entryBefore $entryReplacement $embeddedProfile 'embedded compact'
Build-Replacement $clientBefore $clientReplacement $looseProfile 'loose compact'
Build-Replacement $runtimeBefore $runtimeReplacement $runtimeProfile 'runtime compact'

$entryChanged = $false
$clientChanged = $false
$runtimeChanged = $false
try {
    if ($Apply -and $looseProfile.hash -ne $looseProfile.expectedHash) {
        Copy-Item -LiteralPath $clientReplacement -Destination $clientLoosePath -Force
        $clientChanged = $true
    }
    if ($Apply -and $runtimeProfile.hash -ne $runtimeProfile.expectedHash) {
        Copy-Item -LiteralPath $runtimeReplacement -Destination $runtimePath -Force
        $runtimeChanged = $true
    }
    if ($Apply -and $embeddedProfile.hash -ne $embeddedProfile.expectedHash) {
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $entryReplacement $embeddedProfile.hash
        } "Replacing $entryName"
        $entryChanged = $true
    }

    Export-PakEntry $entryName $entryVerified
    $verifiedExpected = if ($Apply) { $embeddedProfile.expectedHash } else { $embeddedProfile.hash }
    if ((Get-Sha256 $entryVerified) -ne $verifiedExpected) {
        throw "Post-operation verification failed for $entryName"
    }
    if ($Apply -and (Get-Sha256 $clientLoosePath) -ne $looseProfile.expectedHash) {
        throw 'Post-operation verification failed for loose compact'
    }
    if ($Apply -and (Get-Sha256 $runtimePath) -ne $runtimeProfile.expectedHash) {
        throw 'Post-operation verification failed for runtime compact'
    }

    $probeAfter = @{}
    for ($index = 0; $index -lt $probeEntries.Count; $index++) {
        $path = Join-Path $patchRoot "probe-$index.after"
        Export-PakEntry $probeEntries[$index] $path
        $hash = Get-Sha256 $path
        if ($hash -ne $probeBefore[$probeEntries[$index]].hash) {
            throw "Unrelated game_pak entry changed: $($probeEntries[$index])"
        }
        $probeAfter[$probeEntries[$index]] = @{ path = $path; hash = $hash }
    }
}
catch {
    if ($Apply -and $entryChanged) {
        Write-Warning 'Patch failed; restoring the embedded compact entry.'
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $entryBefore $embeddedProfile.expectedHash
        } "Rolling back $entryName"
    }
    if ($Apply -and $runtimeChanged) {
        Copy-Item -LiteralPath $runtimeBefore -Destination $runtimePath -Force
    }
    if ($Apply -and $clientChanged) {
        Copy-Item -LiteralPath $clientBefore -Destination $clientLoosePath -Force
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
elseif (-not $entryChanged) {
    $packageHashBefore
}
else {
    Get-Sha256 $gamePakPath
}

$manifest = [ordered]@{
    schemaVersion = 1
    patchId = 'aa10-erenor-catalog-r575-v1'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = (git -C $repo rev-parse HEAD).Trim()
    applied = [bool]$Apply
    reconstruction = [ordered]@{
        folioCategories = 42
        equipmentGuideRows = @(42, 42, 42, 39)
        synthesisCaps = 78
        addedInfusionAndScrollGuideRows = 6
        inventedItemRecipes = 0
        inventedAwakeningMappings = 0
    }
    gamePak = [ordered]@{
        path = $gamePakPath
        sizeBefore = $packageSizeBefore
        sizeAfter = $packageSizeAfter
        sha256Before = $packageHashBefore
        sha256After = $packageHashAfter
    }
    embeddedCompact = [ordered]@{
        name = $entryName
        sizeBefore = $embeddedProfile.size
        sizeAfter = $embeddedProfile.expectedSize
        sha256Before = $embeddedProfile.hash
        sha256ExpectedAfter = $embeddedProfile.expectedHash
        changed = $entryChanged
        rollbackFile = $entryBefore
        replacementFile = $entryReplacement
    }
    clientLooseCompact = [ordered]@{
        path = $clientLoosePath
        sizeBefore = $looseProfile.size
        sizeAfter = $looseProfile.expectedSize
        sha256Before = $looseProfile.hash
        sha256ExpectedAfter = $looseProfile.expectedHash
        changed = $clientChanged
        rollbackFile = $clientBefore
        replacementFile = $clientReplacement
    }
    runtimeCompact = [ordered]@{
        path = $runtimePath
        sizeBefore = $runtimeProfile.size
        sizeAfter = $runtimeProfile.expectedSize
        sha256Before = $runtimeProfile.hash
        sha256ExpectedAfter = $runtimeProfile.expectedHash
        changed = $runtimeChanged
        rollbackFile = $runtimeBefore
        replacementFile = $runtimeReplacement
    }
    unrelatedEntryProbes = $probeAfter
}
$manifestPath = Join-Path $patchRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Patch mode: $($(if ($Apply) { 'APPLIED' } else { 'DRY RUN' }))"
Write-Host "Embedded compact: $($embeddedProfile.hash) -> $($embeddedProfile.expectedHash)"
Write-Host "Loose compact:    $($looseProfile.hash) -> $($looseProfile.expectedHash)"
Write-Host "Runtime compact:  $($runtimeProfile.hash) -> $($runtimeProfile.expectedHash)"
Write-Host "Rollback and manifest: $patchRoot"
