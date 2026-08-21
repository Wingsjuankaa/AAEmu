[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Begin", "Snapshot", "Finish")]
    [string]$Action,

    [ValidatePattern("^[A-Za-z][A-Za-z0-9]{1,31}$")]
    [string]$CharacterName = "Dannia",

    [ValidatePattern("^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
    [string]$Label = "manual",

    [datetime]$SinceUtc,

    [string]$GameContainer = "aaemu10-game-1",
    [string]$DatabaseContainer = "aaemu10-db-1",
    [string]$ZoneLogPath = "E:\AAEmu\rama_10\runtime\logs\ZoneHost.log",
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $repoRoot "runtime\evidence\quest-phase6"
}

function Invoke-DockerText {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & docker @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }
    return ($output -join [Environment]::NewLine)
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [AllowEmptyString()][string]$Value
    )

    [System.IO.File]::WriteAllText($Path, $Value, [System.Text.UTF8Encoding]::new($false))
}

function ConvertTo-UtcDateTime {
    param([Parameter(Mandatory = $true)][object]$Value)

    # PowerShell 7 ConvertFrom-Json may materialize ISO-8601 properties as DateTime.
    # Parsing that object again first converts it to a culture-specific string (for
    # example 08/20/2026), which fails under day/month cultures such as es-CL.
    if ($Value -is [datetime]) {
        return $Value.ToUniversalTime()
    }
    if ($Value -is [datetimeoffset]) {
        return $Value.UtcDateTime
    }

    return [datetime]::Parse(
        [string]$Value,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}

function Capture-Snapshot {
    param(
        [Parameter(Mandatory = $true)][string]$SessionDirectory,
        [Parameter(Mandatory = $true)][datetime]$StartedUtc,
        [Parameter(Mandatory = $true)][string]$SnapshotLabel
    )

    $existing = @(Get-ChildItem -LiteralPath $SessionDirectory -Directory -ErrorAction SilentlyContinue)
    $sequence = $existing.Count + 1
    $snapshotName = "{0:D3}-{1}" -f $sequence, $SnapshotLabel
    $snapshotDirectory = Join-Path $SessionDirectory $snapshotName
    New-Item -ItemType Directory -Path $snapshotDirectory -Force | Out-Null

    $worldStatus = Invoke-DockerText -Arguments @(
        "exec", $GameContainer, "sh", "-lc",
        "wget -qO- http://127.0.0.1:1280/api/world/zone-manager-status"
    )
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "world-status.json") -Value $worldStatus

    $databaseSql = @"
SET @cid = (SELECT id FROM characters WHERE name = '$CharacterName' AND deleted = 0 LIMIT 1);
SELECT 'character' AS section, id, account_id, name, race, level, experience, world_id,
       zone_id, x, y, z, money, honor_point, vocation_point, updated_at
  FROM characters WHERE id = @cid;
SELECT 'active_quest' AS section, id, template_id, status, HEX(data) AS data_hex, owner
  FROM quests WHERE owner = @cid ORDER BY template_id, id;
SELECT 'completed_quest' AS section, id, HEX(data) AS data_hex, owner
  FROM completed_quests WHERE owner = @cid ORDER BY id;
SELECT 'inventory_item' AS section, id, type, template_id, container_id, slot_type, slot,
       count, owner, grade, flags
  FROM items WHERE owner = @cid ORDER BY container_id, slot, id;
SELECT 'reward_progress' AS section, character_id, leadership_point,
       daily_leadership_point, daily_reset_date
  FROM character_quest_reward_progress WHERE character_id = @cid;
SELECT 'reward_ledger' AS section, HEX(attempt_id) AS attempt_id, act_id, character_id,
       quest_template_id, detail_type, detail_id, status, created_at, completed_at
  FROM quest_reward_ledger WHERE character_id = @cid ORDER BY created_at, act_id;
"@
    $databaseOutput = $databaseSql |
        & docker exec -i $DatabaseContainer sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" aaemu_game --batch --raw' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to capture aaemu_game quest state: $($databaseOutput -join [Environment]::NewLine)"
    }
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "database-state.tsv") `
        -Value ($databaseOutput -join [Environment]::NewLine)

    $since = $StartedUtc.ToUniversalTime().ToString("o")
    $gameLogs = Invoke-DockerText -Arguments @("logs", "--timestamps", "--since", $since, $GameContainer)
    $questPattern = [regex]::Escape($CharacterName) +
        "|Quest|quest|Cinema|cinema|Doodad|doodad|ZoneQuestArea|QuestAreaSphere|WZQuestNpcAi"
    $filteredGameLogs = $gameLogs -split "`r?`n" |
        Select-String -Pattern $questPattern |
        ForEach-Object { $_.Line }
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "game-quest.log") `
        -Value ($filteredGameLogs -join [Environment]::NewLine)

    if (Test-Path -LiteralPath $ZoneLogPath) {
        $zoneLogs = Get-Content -LiteralPath $ZoneLogPath -Tail 20000 |
            Select-String -Pattern "Quest|quest|Cinema|cinema|Doodad|doodad|ZoneLoaded|Heartbeat|WZQuestNpcAi|ZWJoin" |
            ForEach-Object { $_.Line }
        Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "zone-quest.log") `
            -Value ($zoneLogs -join [Environment]::NewLine)
    }

    $containerStatus = & docker inspect $GameContainer $DatabaseContainer 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect Phase 6 containers: $($containerStatus -join [Environment]::NewLine)"
    }
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "containers.json") `
        -Value ($containerStatus -join [Environment]::NewLine)

    $zoneProcesses = Get-CimInstance Win32_Process -Filter "Name = 'AAEmu.ZoneHost.exe'" |
        Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "zone-processes.json") `
        -Value ($zoneProcesses | ConvertTo-Json -Depth 4)

    $metadata = [ordered]@{
        CapturedUtc = [datetime]::UtcNow.ToString("o")
        Action = $Action
        Label = $SnapshotLabel
        CharacterName = $CharacterName
        GameContainer = $GameContainer
        DatabaseContainer = $DatabaseContainer
        ZoneLogPath = $ZoneLogPath
    }
    Write-Utf8NoBom -Path (Join-Path $snapshotDirectory "snapshot.json") `
        -Value ($metadata | ConvertTo-Json -Depth 4)

    return $snapshotDirectory
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$latestPointer = Join-Path $OutputRoot ("latest-{0}.txt" -f $CharacterName)

if ($Action -eq "Begin") {
    $startedUtc = if ($PSBoundParameters.ContainsKey("SinceUtc")) {
        $SinceUtc.ToUniversalTime()
    } else {
        [datetime]::UtcNow
    }
    $sessionName = "{0}-{1}" -f $startedUtc.ToString("yyyyMMdd-HHmmss"), $CharacterName
    $sessionDirectory = Join-Path $OutputRoot $sessionName
    New-Item -ItemType Directory -Path $sessionDirectory -Force | Out-Null

    $session = [ordered]@{
        SchemaVersion = 1
        CharacterName = $CharacterName
        StartedUtc = $startedUtc.ToString("o")
        CompletedUtc = $null
        Status = "running"
        RequiresManualClientControl = $true
        AllowsGmProgression = $false
    }
    Write-Utf8NoBom -Path (Join-Path $sessionDirectory "session.json") `
        -Value ($session | ConvertTo-Json -Depth 4)
    Write-Utf8NoBom -Path $latestPointer -Value $sessionDirectory
} else {
    if (-not (Test-Path -LiteralPath $latestPointer)) {
        throw "No Phase 6 session exists for $CharacterName. Run -Action Begin first."
    }
    $sessionDirectory = (Get-Content -LiteralPath $latestPointer -Raw).Trim()
    if (-not (Test-Path -LiteralPath $sessionDirectory)) {
        throw "The recorded Phase 6 session does not exist: $sessionDirectory"
    }
    $session = Get-Content -LiteralPath (Join-Path $sessionDirectory "session.json") -Raw |
        ConvertFrom-Json
    $startedUtc = ConvertTo-UtcDateTime -Value $session.StartedUtc
}

$snapshotDirectory = Capture-Snapshot -SessionDirectory $sessionDirectory `
    -StartedUtc $startedUtc -SnapshotLabel $Label

if ($Action -eq "Finish") {
    $session.Status = "awaiting-review"
    $session.CompletedUtc = [datetime]::UtcNow.ToString("o")
    Write-Utf8NoBom -Path (Join-Path $sessionDirectory "session.json") `
        -Value ($session | ConvertTo-Json -Depth 4)

    $manifest = Get-ChildItem -LiteralPath $sessionDirectory -File -Recurse |
        Where-Object { $_.Name -ne "manifest.sha256" } |
        Sort-Object FullName |
        ForEach-Object {
            $relativePath = [System.IO.Path]::GetRelativePath($sessionDirectory, $_.FullName)
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            "$hash  $relativePath"
        }
    Write-Utf8NoBom -Path (Join-Path $sessionDirectory "manifest.sha256") `
        -Value ($manifest -join [Environment]::NewLine)
}

Write-Host "Phase 6 evidence captured: $snapshotDirectory"
Write-Host "Session: $sessionDirectory"
