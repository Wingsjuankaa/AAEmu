[CmdletBinding()]
param(
    [string]$Bundle = 'E:\AAEmu\rama_10\artifacts\builds\zonehost\release',
    [string]$BinDirectory = 'E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64',
    [switch]$ApplyPending
)
$ErrorActionPreference = 'Stop'
$BinDirectory = [IO.Path]::GetFullPath($BinDirectory)
if (-not (Test-Path -LiteralPath $BinDirectory -PathType Container)) { throw "Missing runtime Bin64: $BinDirectory" }
$target = Join-Path $BinDirectory 'AAEmu.ZoneHost.exe'
$updates = Join-Path $BinDirectory '.zonehost-updates'
$pendingPath = Join-Path $updates 'pending.json'

function Write-AtomicJson([string]$Path, $Value) {
    $temporary = "$Path.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporary, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temporary, $Path) }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}
function Get-ActiveUsers {
    # Unknown paths also defer publishing: lack of visibility is not proof of absence.
    @(Get-CimInstance Win32_Process -Filter "Name='AAEmu.ZoneHost.exe'" -ErrorAction Stop |
        Where-Object { $null -ne $_ -and (-not $_.ExecutablePath -or [IO.Path]::GetFullPath($_.ExecutablePath) -ieq $target) } |
        ForEach-Object { [int]$_.ProcessId })
}
if ($ApplyPending -and -not (Test-Path -LiteralPath $pendingPath)) {
    @{status='none';target=$target} | ConvertTo-Json -Compress
    return
}
New-Item -ItemType Directory -Path $updates -Force | Out-Null
# File lock covers publisher and all Control Center processes, including other sessions.
$lock = $null
$deadline = [DateTime]::UtcNow.AddSeconds(15)
while (-not $lock) {
    try { $lock = [IO.File]::Open((Join-Path $updates 'publish.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch [IO.IOException] {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Another ZoneHost publication is still running.' }
        Start-Sleep -Milliseconds 100
    }
}
try {
    if (-not $ApplyPending) {
        & (Join-Path $PSScriptRoot 'Test-Candidate.ps1') -Bundle $Bundle | Out-Null
        $manifest = Get-Content -LiteralPath (Join-Path $Bundle 'build-manifest.json') -Raw | ConvertFrom-Json
        if ($manifest.configuration -ne 'Release') { throw 'Only Release builds can be published to Control Center.' }
        $hash = [string]$manifest.binarySha256
        if ($hash -notmatch '^[A-Fa-f0-9]{64}$') { throw 'Invalid candidate SHA-256.' }
        $hash = $hash.ToUpperInvariant()
        $release = Join-Path $updates $hash
        New-Item -ItemType Directory -Path $release -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $Bundle 'AAEmu.ZoneHost.exe') -Destination (Join-Path $release 'AAEmu.ZoneHost.exe') -Force
        Write-AtomicJson (Join-Path $release 'build-manifest.json') $manifest
        $nativeHashes = [ordered]@{}
        foreach ($name in @('x2game-dev_dedicate.dll', 'CrySystem.dll', 'xlcommon.dll')) {
            $nativeHashes[$name] = (Get-FileHash -LiteralPath (Join-Path $BinDirectory $name)).Hash
        }
        Write-AtomicJson $pendingPath ([ordered]@{schemaVersion=1;sha256=$hash;queuedAtUtc=[DateTime]::UtcNow.ToString('o');nativeHashes=$nativeHashes})
    }
    if (-not (Test-Path -LiteralPath $pendingPath)) {
        @{status='none';target=$target} | ConvertTo-Json -Compress
        return
    }
    $pending = Get-Content -LiteralPath $pendingPath -Raw | ConvertFrom-Json
    if ($pending.schemaVersion -ne 1 -or $pending.sha256 -notmatch '^[A-Fa-f0-9]{64}$') { throw 'Invalid pending publication metadata.' }
    $hash = $pending.sha256.ToUpperInvariant()
    foreach ($name in @('x2game-dev_dedicate.dll', 'CrySystem.dll', 'xlcommon.dll')) {
        if (-not $pending.nativeHashes.$name -or
            (Get-FileHash -LiteralPath (Join-Path $BinDirectory $name)).Hash -ne $pending.nativeHashes.$name) {
            throw "Native dependency changed since publication: $name. Rebuild and audit before applying."
        }
    }
    $release = Join-Path $updates $hash
    $candidate = Join-Path $release 'AAEmu.ZoneHost.exe'
    $manifest = Get-Content -LiteralPath (Join-Path $release 'build-manifest.json') -Raw | ConvertFrom-Json
    if ($manifest.configuration -ne 'Release' -or $manifest.binarySha256 -ne $hash -or
        (Get-FileHash -LiteralPath $candidate).Hash -ne $hash) { throw 'Pending ZoneHost integrity check failed; current runtime retained.' }
    & (Join-Path $PSScriptRoot 'Test-Candidate.ps1') -Bundle $release | Out-Null
    $previousHash = if (Test-Path -LiteralPath $target) { (Get-FileHash -LiteralPath $target).Hash } else { $null }
    $backup = $null
    $state = 'current'
    if ($previousHash -ne $hash) {
        $active = @(Get-ActiveUsers)
        if ($active.Count -gt 0) {
            @{status='pending';target=$target;sha256=$hash;activeProcessIds=$active;reason='Executable in use; active Zones are unchanged.'} | ConvertTo-Json -Compress
            return
        }
        $temporary = Join-Path $BinDirectory ('.zonehost-install-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        try {
            Copy-Item -LiteralPath $candidate -Destination $temporary
            if ((Get-FileHash -LiteralPath $temporary).Hash -ne $hash) { throw 'Staged install hash mismatch.' }
            if ($previousHash) {
                $backups = Join-Path $updates 'backups'
                New-Item -ItemType Directory -Path $backups -Force | Out-Null
                $backup = Join-Path $backups (([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff')) + '-' + $previousHash + '.exe')
                # ReplaceFile is atomic; sharing violations leave the old executable in place.
                [IO.File]::Replace($temporary, $target, $backup)
            } else { [IO.File]::Move($temporary, $target) }
        } catch {
            $active = @(Get-ActiveUsers)
            if ($active.Count -gt 0) {
                @{status='pending';target=$target;sha256=$hash;activeProcessIds=$active;reason='A Zone started during publication; retry before next launch.'} | ConvertTo-Json -Compress
                return
            }
            throw
        } finally {
            if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
        }
        if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) { throw "Published hash mismatch; previous binary preserved at $backup" }
        $state = 'published'
    }
    $installedPath = Join-Path $updates 'installed.json'
    if ($state -eq 'current' -and (Test-Path -LiteralPath $installedPath)) {
        $prior = Get-Content -LiteralPath $installedPath -Raw | ConvertFrom-Json
        if ($prior.sha256 -eq $hash) { $backup = $prior.backup; $previousHash = $prior.previousSha256 }
    }
    Write-AtomicJson $installedPath ([ordered]@{
        schemaVersion=1;sha256=$hash;installedAtUtc=[DateTime]::UtcNow.ToString('o');previousSha256=$previousHash;backup=$backup;build=$manifest
    })
    Remove-Item -LiteralPath $pendingPath
    @{status=$state;target=$target;sha256=$hash;backup=$backup} | ConvertTo-Json -Compress
} finally { $lock.Dispose() }
