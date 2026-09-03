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
$builder = Join-Path $repo 'Scripts\PatchAa10ItemStackLimit.py'
$entryName = 'game/db/compact.sqlite3'

$entrySize = 440823808
$entryTransitions = @{
    'E8526ADDDE49BB4F2162106F6A7B494967B57D1596BBFA4A0B06931335AA9E5E' = '49718904E9D318B043A563BDE92A33ACB86B0FA18DF3046D821E59E14B4F496F'
    '84038AAF7EEE120A4218F8B1CE5FE14E1D9C949B8F92814BB4A040128D676BE8' = '7472265C95AB20E1E13D9BBD696258E25704C67D405DEF249784FBFA0AD50C74'
    '49718904E9D318B043A563BDE92A33ACB86B0FA18DF3046D821E59E14B4F496F' = '49718904E9D318B043A563BDE92A33ACB86B0FA18DF3046D821E59E14B4F496F'
    '7472265C95AB20E1E13D9BBD696258E25704C67D405DEF249784FBFA0AD50C74' = '7472265C95AB20E1E13D9BBD696258E25704C67D405DEF249784FBFA0AD50C74'
}
$clientLooseSize = 440832000
$clientLooseTransitions = @{
    'D27C55FD1F1F4CFE5307198F96D6E30F73AC9CACAC130B4B1F7876C20C8ADD0B' = 'B506E824EC1EB70295925D5153344CE48BE247C4987F3D95224CB56553A56F81'
    'FEFD3700177EFDE7B16176A229B92A4F2048C34E07DCB088E0E8F56F00625772' = 'F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75'
    'B506E824EC1EB70295925D5153344CE48BE247C4987F3D95224CB56553A56F81' = 'B506E824EC1EB70295925D5153344CE48BE247C4987F3D95224CB56553A56F81'
    'F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75' = 'F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75'
}
$runtimeSize = 552178688
$runtimeTransitions = @{
    'DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD' = 'A0B9BFCE84674619C455880D4153C782C2AAE04B7B1273620A416614CE167096'
    '12C9A1254306E1677807EE57F77A37F2262814D624FE8E66DB7F438BEB9ECCA2' = '1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D'
    'A0B9BFCE84674619C455880D4153C782C2AAE04B7B1273620A416614CE167096' = 'A0B9BFCE84674619C455880D4153C782C2AAE04B7B1273620A416614CE167096'
    '1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D' = '1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D'
}

$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-item-stack-limit-$timestamp"
if (Test-Path -LiteralPath $patchRoot) {
    throw "Refusing to reuse patch directory: $patchRoot"
}
New-Item -ItemType Directory -Path $patchRoot | Out-Null

$entryBefore = Join-Path $patchRoot 'compact.pak.before.sqlite3'
$entryReplacement = Join-Path $patchRoot 'compact.pak.replacement.sqlite3'
$entryVerified = Join-Path $patchRoot 'compact.pak.verified.sqlite3'
$clientLooseBefore = Join-Path $patchRoot 'compact.client-loose.before.sqlite3'
$clientLooseReplacement = Join-Path $patchRoot 'compact.client-loose.replacement.sqlite3'
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

function Assert-Identity {
    param(
        [string]$Path,
        [long]$ExpectedSize,
        [hashtable]$Transitions,
        [string]$Label
    )
    $actualSize = (Get-Item -LiteralPath $Path).Length
    $actualHash = Get-Sha256 $Path
    if ($actualSize -ne $ExpectedSize) {
        throw "$Label has unexpected size $actualSize (expected $ExpectedSize)"
    }
    if (-not $Transitions.ContainsKey($actualHash)) {
        throw "$Label has unexpected SHA-256 $actualHash"
    }
    return $actualHash
}

function Export-Compact([string]$Output) {
    Invoke-Checked {
        dotnet run --project $extractProject --configuration Release -- `
            $gamePakPath $entryName $Output
    } "Extracting $entryName"
}

function Build-Replacement {
    param(
        [string]$Source,
        [string]$Output,
        [long]$ExpectedSize,
        [string]$ExpectedPatchedHash,
        [string]$Label
    )
    Copy-Item -LiteralPath $Source -Destination $Output
    Invoke-Checked {
        python -B $builder $Output --apply
    } "Building $Label"
    if ((Get-Item -LiteralPath $Output).Length -ne $ExpectedSize) {
        throw "$Label replacement does not preserve its exact size"
    }
    $outputHash = Get-Sha256 $Output
    if ($outputHash -ne $ExpectedPatchedHash) {
        throw "$Label replacement is not deterministic: $outputHash"
    }
}

$packageSizeBefore = (Get-Item -LiteralPath $gamePakPath).Length
$packageHashBefore = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }

Export-Compact $entryBefore
Copy-Item -LiteralPath $clientLoosePath -Destination $clientLooseBefore
Copy-Item -LiteralPath $runtimePath -Destination $runtimeBefore

$entryHashBefore = Assert-Identity $entryBefore $entrySize $entryTransitions $entryName
$clientLooseHashBefore = Assert-Identity $clientLooseBefore $clientLooseSize $clientLooseTransitions 'client loose compact'
$runtimeHashBefore = Assert-Identity $runtimeBefore $runtimeSize $runtimeTransitions 'AAEmu runtime compact'
$entryExpectedAfter = $entryTransitions[$entryHashBefore]
$clientLooseExpectedAfter = $clientLooseTransitions[$clientLooseHashBefore]
$runtimeExpectedAfter = $runtimeTransitions[$runtimeHashBefore]

$needsEntryPatch = $entryHashBefore -ne $entryExpectedAfter
$needsClientLoosePatch = $clientLooseHashBefore -ne $clientLooseExpectedAfter
$needsRuntimePatch = $runtimeHashBefore -ne $runtimeExpectedAfter
if ($Apply -and ($needsEntryPatch -or $needsClientLoosePatch) -and (Get-Process -Name archeage -ErrorAction SilentlyContinue)) {
    throw 'Close archeage.exe before applying the AA10 item-stack patch.'
}

Build-Replacement $entryBefore $entryReplacement $entrySize $entryExpectedAfter 'embedded client compact'
Build-Replacement $clientLooseBefore $clientLooseReplacement $clientLooseSize $clientLooseExpectedAfter 'loose client compact'
Build-Replacement $runtimeBefore $runtimeReplacement $runtimeSize $runtimeExpectedAfter 'AAEmu runtime compact'

$entryChanged = $false
$clientLooseChanged = $false
$runtimeChanged = $false
try {
    if ($Apply -and $needsClientLoosePatch) {
        Copy-Item -LiteralPath $clientLooseReplacement -Destination $clientLoosePath -Force
        $clientLooseChanged = $true
    }
    if ($Apply -and $needsRuntimePatch) {
        Copy-Item -LiteralPath $runtimeReplacement -Destination $runtimePath -Force
        $runtimeChanged = $true
    }
    if ($Apply -and $needsEntryPatch) {
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $entryReplacement $entryHashBefore
        } "Replacing $entryName"
        $entryChanged = $true
    }

    if ($Apply) {
        Export-Compact $entryVerified
        if ((Get-Sha256 $entryVerified) -ne $entryExpectedAfter) {
            throw "Post-operation verification failed for $entryName"
        }
        if ((Get-Sha256 $clientLoosePath) -ne $clientLooseExpectedAfter) {
            throw 'Post-operation verification failed for client loose compact'
        }
        if ((Get-Sha256 $runtimePath) -ne $runtimeExpectedAfter) {
            throw 'Post-operation verification failed for AAEmu runtime compact'
        }
    }
    else {
        Copy-Item -LiteralPath $entryBefore -Destination $entryVerified
    }
}
catch {
    if ($Apply -and $entryChanged) {
        Write-Warning 'Patch failed; restoring the embedded compact entry.'
        Invoke-Checked {
            dotnet run --project $replaceProject --configuration Release -- `
                $gamePakPath $entryName $entryBefore $entryExpectedAfter
        } "Rolling back $entryName"
    }
    if ($Apply -and $runtimeChanged) {
        Copy-Item -LiteralPath $runtimeBefore -Destination $runtimePath -Force
    }
    if ($Apply -and $clientLooseChanged) {
        Copy-Item -LiteralPath $clientLooseBefore -Destination $clientLoosePath -Force
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
    patchId = 'aa10-item-stack-limit-99999-r575-v2'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = (git -C $repo rev-parse HEAD).Trim()
    applied = [bool]$Apply
    sourceLimits = @(1000, 9999)
    targetLimit = 99999
    gamePak = [ordered]@{
        path = $gamePakPath
        sizeBefore = $packageSizeBefore
        sizeAfter = $packageSizeAfter
        sha256Before = $packageHashBefore
        sha256After = $packageHashAfter
    }
    embeddedCompact = [ordered]@{
        name = $entryName
        size = $entrySize
        sha256Before = $entryHashBefore
        sha256ExpectedAfter = $entryExpectedAfter
        sha256Verified = if ($Apply) { Get-Sha256 $entryVerified } else { $entryHashBefore }
        changed = $entryChanged
        rollbackFile = $entryBefore
        replacementFile = $entryReplacement
    }
    clientLooseCompact = [ordered]@{
        path = $clientLoosePath
        size = $clientLooseSize
        sha256Before = $clientLooseHashBefore
        sha256ExpectedAfter = $clientLooseExpectedAfter
        changed = $clientLooseChanged
        rollbackFile = $clientLooseBefore
        replacementFile = $clientLooseReplacement
    }
    runtimeCompact = [ordered]@{
        path = $runtimePath
        size = $runtimeSize
        sha256Before = $runtimeHashBefore
        sha256ExpectedAfter = $runtimeExpectedAfter
        changed = $runtimeChanged
        rollbackFile = $runtimeBefore
        replacementFile = $runtimeReplacement
    }
}
$manifestPath = Join-Path $patchRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Patch mode: $($(if ($Apply) { 'APPLIED' } else { 'DRY RUN' }))"
Write-Host 'Stack limits: 1000/9999 -> 99999'
Write-Host "Embedded compact SHA-256: $entryHashBefore -> $entryExpectedAfter"
Write-Host "Runtime compact SHA-256:  $runtimeHashBefore -> $runtimeExpectedAfter"
Write-Host "Rollback and manifest: $patchRoot"
Write-Host "Manifest: $manifestPath"
