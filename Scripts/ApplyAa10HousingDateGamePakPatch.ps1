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
$builder = Join-Path $repo 'Scripts\PatchAa10HousingDateFormatting.py'
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssZ')
$patchRoot = Join-Path $BackupRoot "aa10-housing-date-format-$timestamp"

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
        Name = 'maintain_window'
        SourceEntry = 'game/scripts/x2ui/housing/maintain_window.lua'
        AlbEntry = 'game/scriptsbin64/x2ui/housing/maintain_window.alb'
        OriginalHash = 'CA446A2D1FA6DB2F3C96AEB73AD206B93707FF637C09A75082129D6DE5677736'
        PatchedHash = 'CA19CCE55ECBCB1C8C165BD28B762905FB98C3F99172639580742CD559A789CD'
        Size = 16432
    },
    [pscustomobject]@{
        Name = 'maintain_window_view'
        SourceEntry = 'game/scripts/x2ui/housing/maintain_window_view.lua'
        AlbEntry = 'game/scriptsbin64/x2ui/housing/maintain_window_view.alb'
        OriginalHash = 'A946192136A542998B5AE12C989B774D2DBEE47FB024F39A26F33B55A304E105'
        PatchedHash = '8C6F73F36B827C4072D8078ABA649F7E51B5D44A19F9A7DC20F97FF4AFFC416E'
        Size = 39389
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
        dotnet run --project $extractProject --configuration Release -- $gamePakPath $Entry $Output
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
        --maintain-source (Join-Path $extracted 'maintain_window.lua') `
        --maintain-alb (Join-Path $extracted 'maintain_window.before.alb') `
        --view-source (Join-Path $extracted 'maintain_window_view.lua') `
        --view-alb (Join-Path $extracted 'maintain_window_view.before.alb') `
        --luac $luacPath `
        --output-dir $replacements
} 'Building Housing date replacements'

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
                dotnet run --project $replaceProject --configuration Release -- `
                    $gamePakPath $entry.AlbEntry $entry.Replacement $entry.OriginalHash
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
                dotnet run --project $replaceProject --configuration Release -- `
                    $gamePakPath $entry.AlbEntry $entry.AlbBackup $entry.PatchedHash
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
    patchId = 'aa10-housing-calendar-date-r575'
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    repositoryHead = $repoHead
    applied = [bool]$Apply
    gamePak = [ordered]@{
        path = $gamePakPath
        sizeBefore = $packageSizeBefore
        sizeAfter = $packageSizeAfter
        sha256Before = $packageHashBefore
        sha256After = $packageHashAfter
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
