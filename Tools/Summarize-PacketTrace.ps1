param(
    [string]$Path = "",
    [int]$Tail = 80
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Path)) {
    $traceRoot = Join-Path $PSScriptRoot "..\runtime-captures\packet-traces"
    $latest = Get-ChildItem -LiteralPath $traceRoot -Filter "aa8-*-*.jsonl" |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($null -eq $latest) {
        throw "No packet trace was found in $traceRoot"
    }
    $Path = $latest.FullName
}

$events = Get-Content -LiteralPath $Path |
    ForEach-Object { $_ | ConvertFrom-Json }

Write-Output "Trace: $Path"
Write-Output "Events: $($events.Count)"

$events |
    Select-Object -Last $Tail |
    ForEach-Object {
        $opcode = if ($null -ne $_.opcodeHex) { $_.opcodeHex } else { "-" }
        $packet = if ($null -ne $_.packetType) {
            ($_.packetType -split '\.')[-1]
        } else {
            "-"
        }
        "{0,6} {1,8}ms {2,-18} L={3} OP={4,-5} {5,-36} bytes={6} {7}" -f `
            $_.seq, $_.elapsedMs, $_.kind, $_.level, $opcode, $packet,
            $_.length, $_.details
    }
