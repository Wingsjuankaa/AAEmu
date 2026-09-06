[CmdletBinding()]
param([string]$Bundle = 'E:\AAEmu\rama_10\artifacts\builds\zonehost\release')
$ErrorActionPreference = 'Stop'
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('aaemu-zonehost-publication-' + [Guid]::NewGuid().ToString('N'))
$bin = Join-Path $fixture 'Bin64'
New-Item -ItemType Directory -Path $bin -Force | Out-Null
$target = Join-Path $bin 'AAEmu.ZoneHost.exe'
[IO.File]::WriteAllText($target, 'previous-executable-fixture')
foreach ($name in @('x2game-dev_dedicate.dll','CrySystem.dll','xlcommon.dll')) {
    [IO.File]::WriteAllText((Join-Path $bin $name), 'native-dependency-fixture')
}
$previousHash = (Get-FileHash -LiteralPath $target).Hash
$candidateHash = (Get-FileHash -LiteralPath (Join-Path $Bundle 'AAEmu.ZoneHost.exe')).Hash
$global:ZoneHostPublicationTestProcesses = @([pscustomobject]@{ProcessId=12345;ExecutablePath=$target})
# Scoped process inventory shim. No real Zone process is started, stopped or hidden.
function Get-CimInstance { param($ClassName, $Filter, $ErrorAction) $global:ZoneHostPublicationTestProcesses }
function Assert([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
$publisher = Join-Path $PSScriptRoot 'Publish-ZoneHost.ps1'
$result = (& $publisher -Bundle $Bundle -BinDirectory $bin) | ConvertFrom-Json
Assert ($result.status -eq 'pending') 'Active process did not defer publication.'
Assert ($result.activeProcessIds[0] -eq 12345) 'Unexpected process inventory.'
Assert ((Get-FileHash -LiteralPath $target).Hash -eq $previousHash) 'Active binary was changed.'
'PASS: queues update and preserves active binary.'
$pending = Join-Path $bin '.zonehost-updates/pending.json'
$global:ZoneHostPublicationTestProcesses = @([pscustomobject]@{ProcessId=12345;ExecutablePath=$null})
$result = (& $publisher -ApplyPending -BinDirectory $bin) | ConvertFrom-Json
Assert ($result.status -eq 'pending') 'Unknown process path must defer publication.'
'PASS: unknown executable path fails closed.'
$global:ZoneHostPublicationTestProcesses = @()
$held = [IO.File]::Open($target, 'Open', 'Read', 'Read')
$rejected = $false
try { & $publisher -ApplyPending -BinDirectory $bin | Out-Null } catch { $rejected = $true }
finally { $held.Dispose() }
Assert $rejected 'An OS-locked executable was replaced.'
Assert ((Get-FileHash -LiteralPath $target).Hash -eq $previousHash) 'Sharing failure changed the old binary.'
Assert (Test-Path -LiteralPath $pending) 'Sharing failure lost the pending build.'
'PASS: OS sharing violation preserves old binary and pending update.'
$result = (& $publisher -ApplyPending -BinDirectory $bin) | ConvertFrom-Json
Assert ($result.status -eq 'published') "Pending update was not applied: $($result | ConvertTo-Json -Compress)"
Assert ((Get-FileHash -LiteralPath $target).Hash -eq $candidateHash) 'Published binary mismatch.'
Assert ((Get-FileHash -LiteralPath $result.backup).Hash -eq $previousHash) 'Rollback binary was not preserved.'
Assert (-not (Test-Path -LiteralPath $pending)) 'Pending marker not cleared.'
$backup = $result.backup
'PASS: applies atomically and retains exact rollback.'
$result = (& $publisher -Bundle $Bundle -BinDirectory $bin) | ConvertFrom-Json
Assert ($result.status -eq 'current' -and $result.backup -eq $backup) 'Idempotent publication lost rollback metadata.'
'PASS: repeat publication is idempotent.'
# Simulate a stale pending update after a native DLL changes.
$nativeHashes = [ordered]@{}
foreach ($name in @('x2game-dev_dedicate.dll','CrySystem.dll','xlcommon.dll')) { $nativeHashes[$name]=(Get-FileHash -LiteralPath (Join-Path $bin $name)).Hash }
@{schemaVersion=1;sha256=$candidateHash;nativeHashes=$nativeHashes} | ConvertTo-Json | Set-Content -LiteralPath $pending
[IO.File]::AppendAllText((Join-Path $bin 'CrySystem.dll'), 'changed')
$rejected = $false
try { & $publisher -ApplyPending -BinDirectory $bin | Out-Null } catch { $rejected = $_.Exception.Message -like '*Native dependency changed*' }
Assert $rejected 'Changed DLL was accepted.'
Assert ((Get-FileHash -LiteralPath $target).Hash -eq $candidateHash) 'Stale pending update changed runtime.'
'PASS: rejects changed native dependencies without replacing runtime.'
# Integrity rejection must happen before running a corrupt candidate.
[IO.File]::WriteAllText((Join-Path $bin 'CrySystem.dll'), 'native-dependency-fixture')
$staged = Join-Path $bin ".zonehost-updates/$candidateHash/AAEmu.ZoneHost.exe"
[IO.File]::AppendAllText($staged, 'tampered')
$rejected = $false
try { & $publisher -ApplyPending -BinDirectory $bin | Out-Null } catch { $rejected = $_.Exception.Message -like '*integrity check failed*' }
Assert $rejected 'Tampered candidate was accepted.'
Assert ((Get-FileHash -LiteralPath $target).Hash -eq $candidateHash) 'Corrupt candidate changed runtime.'
'PASS: rejects corrupt staged binary without replacing runtime.'
Write-Output "Publication test evidence retained at $fixture"
