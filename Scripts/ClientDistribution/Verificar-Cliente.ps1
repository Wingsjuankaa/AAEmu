$ErrorActionPreference = 'Stop'
$clientManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MANIFEST-SHA256.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$clientRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
$clientFailures = 0
$clientIndex = 0
foreach ($clientFile in $clientManifest.files) {
    $clientIndex++
    $clientTarget = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $clientFile.path))
    if (-not $clientTarget.StartsWith($clientRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path' }
    Write-Progress -Activity 'Verificando cliente' -Status $clientFile.path -PercentComplete (100*$clientIndex/$clientManifest.files.Count)
    if (-not (Test-Path -LiteralPath $clientTarget -PathType Leaf)) {
        Write-Host ('FALTA: ' + $clientFile.path); $clientFailures++; continue
    }
    if ((Get-Item -LiteralPath $clientTarget).Length -ne $clientFile.bytes -or
        (Get-FileHash -LiteralPath $clientTarget -Algorithm SHA256).Hash -ne $clientFile.sha256) {
        Write-Host ('DIFERENTE: ' + $clientFile.path); $clientFailures++
    }
}
Write-Progress -Activity 'Verificando cliente' -Completed
if ($clientFailures) { Write-Host ('Archivos con problemas: ' + $clientFailures); exit 1 }
Write-Host 'OK: todos los archivos coinciden con esta version de la alpha.'
