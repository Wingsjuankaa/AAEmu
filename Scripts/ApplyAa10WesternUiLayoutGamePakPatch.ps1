[CmdletBinding()]
param(
    [string]$GamePak = 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview\game_pak',
    [string]$Luac = 'E:\AAEmu-Research\work\lua-5.1.5-msvc\lua-5.1.5\src\luac51.exe',
    [string]$BackupRoot = 'E:\AAEmu\rama_10\backups\client-patches',
    [switch]$Apply,
    [switch]$SkipFullPakHash
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gamePakPath = (Resolve-Path -LiteralPath $GamePak).Path
$clientRoot = Split-Path -Parent $gamePakPath
$x2gamePath = Join-Path $clientRoot 'Bin64\x2game.dll'
$luacPath = (Resolve-Path -LiteralPath $Luac).Path
$extractTool = Join-Path $repo 'reconstruccion_cliente_10\tools\PakEntryExtract\bin\Release\net10.0\PakEntryExtract.dll'
$replaceTool = Join-Path $repo 'Tools\PakEntryReplace\bin\Release\net10.0\PakEntryReplace.dll'
$builder = Join-Path $repo 'Scripts\PatchAa10WesternUiLayout.py'
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-western-ui-layout-$timestamp"

$expectedX2Game = '405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734'
$actualX2Game = (Get-FileHash -Algorithm SHA256 -LiteralPath $x2gamePath).Hash.ToUpperInvariant()
if ($actualX2Game -ne $expectedX2Game) {
    throw "Unexpected x2game.dll SHA-256 $actualX2Game; expected r575 $expectedX2Game"
}

if ($Apply) {
    $running = Get-CimInstance Win32_Process -Filter "Name = 'archeage.exe'" |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($clientRoot, [StringComparison]::OrdinalIgnoreCase) }
    if ($running) {
        throw "archeage.exe is using $clientRoot. Close only that client before applying the patch."
    }
}

if (Test-Path -LiteralPath $patchRoot) {
    throw "Refusing to reuse patch directory: $patchRoot"
}
New-Item -ItemType Directory -Path $patchRoot | Out-Null
$extracted = Join-Path $patchRoot 'extracted'
$replacements = Join-Path $patchRoot 'replacements'
$verified = Join-Path $patchRoot 'verified'
New-Item -ItemType Directory -Path $extracted, $replacements, $verified | Out-Null

$entries = @(
    [pscustomobject]@{
        Name = 'crafting_view'
        SourceEntry = 'game/scripts/x2ui/crafting/crafting_view.lua'
        AlbEntry = 'game/scriptsbin64/x2ui/crafting/crafting_view.alb'
        OriginalHash = '0B65638618E3F588C8EDDF98832BC076ABD8DD0159DF6F736AC94BFA429C7AF6'
        PatchedHash = '067B69FA6664CACC3D0239F31405A743D958C0BD7811D6B604F8AA93B35756F7'
        Size = 51452
    },
    [pscustomobject]@{
        Name = 'tooltip'
        SourceEntry = 'game/scripts/x2ui/components/tooltip/tooltip.lua'
        AlbEntry = 'game/scriptsbin64/x2ui/components/tooltip/tooltip.alb'
        OriginalHash = 'F725001F508C86DC8579333830964CFE7CE673A86F5FC301864C996929A040AF'
        PatchedHash = '3215CAC0947058F6C47715EAF55C85DC9029C49E6248D593DF2147DF2EE4ED91'
        Size = 266870
    }
)

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
        dotnet $extractTool $gamePakPath $Entry $Output
    } "Extracting $Entry"
}

$packageSizeBefore = (Get-Item -LiteralPath $gamePakPath).Length
$packageHashBefore = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }

foreach ($entry in $entries) {
    $sourceOutput = Join-Path $extracted "$($entry.Name).lua"
    $albOutput = Join-Path $extracted "$($entry.Name).before.alb"
    Export-PakEntry $entry.SourceEntry $sourceOutput
    Export-PakEntry $entry.AlbEntry $albOutput

    $currentHash = Get-Sha256 $albOutput
    if ($currentHash -ne $entry.OriginalHash -and $currentHash -ne $entry.PatchedHash) {
        throw "Unexpected $($entry.AlbEntry) SHA-256 $currentHash"
    }
    if ((Get-Item -LiteralPath $albOutput).Length -ne $entry.Size) {
        throw "Unexpected $($entry.AlbEntry) size"
    }
    $entry | Add-Member -NotePropertyName CurrentHash -NotePropertyValue $currentHash
    $entry | Add-Member -NotePropertyName SourceBackup -NotePropertyValue $sourceOutput
    $entry | Add-Member -NotePropertyName AlbBackup -NotePropertyValue $albOutput
}

Invoke-Checked {
    python $builder `
        --crafting-source (Join-Path $extracted 'crafting_view.lua') `
        --crafting-alb (Join-Path $extracted 'crafting_view.before.alb') `
        --tooltip-source (Join-Path $extracted 'tooltip.lua') `
        --tooltip-alb (Join-Path $extracted 'tooltip.before.alb') `
        --luac $luacPath `
        --output-dir $replacements
} 'Building Western UI replacements'

foreach ($entry in $entries) {
    $replacement = Join-Path $replacements "$($entry.Name).alb"
    if ((Get-Item -LiteralPath $replacement).Length -ne $entry.Size) {
        throw "Generated $($entry.Name) size differs from the PAK entry"
    }
    if ((Get-Sha256 $replacement) -ne $entry.PatchedHash) {
        throw "Generated $($entry.Name) hash is not deterministic"
    }
    $entry | Add-Member -NotePropertyName Replacement -NotePropertyValue $replacement
}

$changed = [System.Collections.Generic.List[object]]::new()
try {
    if ($Apply) {
        foreach ($entry in $entries) {
            Invoke-Checked {
                dotnet $replaceTool $gamePakPath $entry.AlbEntry $entry.Replacement $entry.OriginalHash
            } "Replacing $($entry.AlbEntry)"
            if ($entry.CurrentHash -eq $entry.OriginalHash) {
                $changed.Add($entry)
            }
        }
    }

    foreach ($entry in $entries) {
        $verifyOutput = Join-Path $verified "$($entry.Name).alb"
        if ($Apply) {
            Export-PakEntry $entry.AlbEntry $verifyOutput
            $expectedHash = $entry.PatchedHash
        }
        else {
            Copy-Item -LiteralPath $entry.AlbBackup -Destination $verifyOutput
            $expectedHash = $entry.CurrentHash
        }
        $verifiedHash = Get-Sha256 $verifyOutput
        if ($verifiedHash -ne $expectedHash) {
            throw "Post-operation verification failed for $($entry.AlbEntry): $verifiedHash"
        }
        $entry | Add-Member -NotePropertyName VerifiedHash -NotePropertyValue $verifiedHash
    }
}
catch {
    if ($Apply -and $changed.Count -gt 0) {
        Write-Warning 'Patch failed; rolling back entries changed by this invocation.'
        for ($index = $changed.Count - 1; $index -ge 0; $index--) {
            $entry = $changed[$index]
            Invoke-Checked {
                dotnet $replaceTool $gamePakPath $entry.AlbEntry $entry.AlbBackup $entry.PatchedHash
            } "Rolling back $($entry.AlbEntry)"
        }
    }
    throw
}

$packageSizeAfter = (Get-Item -LiteralPath $gamePakPath).Length
if ($packageSizeAfter -ne $packageSizeBefore) {
    throw "game_pak size changed: $packageSizeBefore -> $packageSizeAfter"
}
$packageHashAfter = if ($SkipFullPakHash) { $null } else { Get-Sha256 $gamePakPath }
$repoHead = (git -C $repo rev-parse HEAD).Trim()

$manifest = [ordered]@{
    schemaVersion = 1
    patchId = 'aa10-western-ui-layout-r575'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = $repoHead
    applied = [bool]$Apply
    clientRoot = $clientRoot
    x2gameSha256 = $actualX2Game
    gamePak = [ordered]@{
        path = $gamePakPath
        sizeBefore = $packageSizeBefore
        sizeAfter = $packageSizeAfter
        sha256Before = $packageHashBefore
        sha256After = $packageHashAfter
    }
    layout = [ordered]@{
        folioWindowWidth = 900
        equipmentTooltipMinimumWidth = 360
    }
    entries = @($entries | ForEach-Object {
        [ordered]@{
            entry = $_.AlbEntry
            size = $_.Size
            sha256Before = $_.CurrentHash
            sha256ExpectedOriginal = $_.OriginalHash
            sha256ExpectedPatched = $_.PatchedHash
            sha256Verified = $_.VerifiedHash
            rollbackFile = $_.AlbBackup
            replacementFile = $_.Replacement
            sourceEntry = $_.SourceEntry
            sourceFile = $_.SourceBackup
        }
    })
}
$manifestPath = Join-Path $patchRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Patch mode: $($(if ($Apply) { 'APPLIED' } else { 'DRY RUN' }))"
Write-Host "Rollback and manifest: $patchRoot"
Write-Host "Manifest: $manifestPath"
