[CmdletBinding()]
param([string]$Bundle = 'E:\AAEmu\rama_10\artifacts\builds\zonehost\release')
$ErrorActionPreference = 'Stop'
$binary = Join-Path $Bundle 'AAEmu.ZoneHost.exe'
$manifest = Get-Content -LiteralPath (Join-Path $Bundle 'build-manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $binary).Hash -ne $manifest.binarySha256) { throw 'Candidate binary hash differs from build manifest.' }
# Every case is rejected by parse_options(), before run() or any native DLL loading.
$cases = @(
    @{arguments='--aaemu-zone-host';message='--native-dll is required'},
    @{arguments='--aaemu-zone-host --invalid-preflight value';message='Unknown zone-host option'},
    @{arguments='--aaemu-zone-host --native-dll';message='Incomplete zone-host option'}
)
foreach ($case in $cases) {
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $binary
    $start.Arguments = $case.arguments
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        [void]$process.Start()
        if (-not $process.WaitForExit(10000)) { $process.Kill(); throw 'Candidate parser probe timed out.' }
        $stderr = $process.StandardError.ReadToEnd()
        if ($process.ExitCode -ne 1 -or -not $stderr.Contains($case.message)) {
            throw "Unexpected parser result: exit=$($process.ExitCode), stderr=$stderr"
        }
        Write-Output "PASS: $($case.message) (native runtime not invoked)."
    } finally { $process.Dispose() }
}
