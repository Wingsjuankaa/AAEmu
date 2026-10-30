[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$projectRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $projectRepository.Equals('E:\AAEmu\rama_10\server\AAEmu', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Install these AA10 skills from the canonical repository on E.'
}
$sourceRoot = Join-Path $projectRepository 'Skills\aa10'
$installedRoot = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex\skills'))
$backupRoot = Join-Path $projectRepository ('..\..\runtime\sandbox-aa10\backups\skills\' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
$backupRoot = [IO.Path]::GetFullPath($backupRoot)
$expectedBackupParent = [IO.Path]::GetFullPath((Join-Path $projectRepository '..\..\runtime\sandbox-aa10\backups\skills'))
if (-not $backupRoot.StartsWith($expectedBackupParent + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unexpected backup destination.'
}
$names = @('aaemu10-native-reconstruction', 'aa10-client-forensics', 'aa10-es-es-localization')
$plans = foreach ($name in $names) {
    $source = [IO.Path]::GetFullPath((Join-Path $sourceRoot $name))
    $installed = [IO.Path]::GetFullPath((Join-Path $installedRoot $name))
    if ([IO.Path]::GetDirectoryName($source) -ne $sourceRoot -or [IO.Path]::GetDirectoryName($installed) -ne $installedRoot) {
        throw 'Skill path escaped its explicitly named parent.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md') -PathType Leaf)) {
        throw "Missing versioned skill: $name"
    }
    $existing = Get-Item -LiteralPath $installed -Force -ErrorAction SilentlyContinue
    $same = $false
    if ($existing -and $existing.LinkType) {
        if ($existing.LinkType -ne 'Junction' -or @($existing.Target).Count -ne 1 -or
            [IO.Path]::GetFullPath([string](@($existing.Target)[0])) -ne $source) {
            throw "The installed skill has an unrelated link; leaving it intact: $name"
        }
        $same = $true
    } elseif ($existing -and -not $existing.PSIsContainer) {
        throw "The installed skill is not a directory: $name"
    }
    [pscustomobject]@{ Name=$name; Source=$source; Installed=$installed; AlreadyLinked=$same; Exists=([bool]$existing) }
}
if (-not $Apply) {
    $plans | Select-Object Name, AlreadyLinked, Source, Installed
    return
}
New-Item -ItemType Directory -Force -Path $installedRoot | Out-Null
foreach ($plan in $plans) {
    if ($plan.AlreadyLinked) {
        Write-Output "OK: $($plan.Name) already uses its versioned source on E."
        continue
    }
    $backup = Join-Path $backupRoot $plan.Name
    # Exact roots were checked above. Preserve the complete previous skill before replacing its path.
    if ($plan.Exists) {
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        Move-Item -LiteralPath $plan.Installed -Destination $backup
    }
    try {
        New-Item -ItemType Junction -Path $plan.Installed -Target $plan.Source | Out-Null
    } catch {
        if ($plan.Exists -and -not (Test-Path -LiteralPath $plan.Installed)) {
            Move-Item -LiteralPath $backup -Destination $plan.Installed
        }
        throw
    }
    Write-Output "OK: $($plan.Name) linked to E; previous directory preserved under $backupRoot."
}
