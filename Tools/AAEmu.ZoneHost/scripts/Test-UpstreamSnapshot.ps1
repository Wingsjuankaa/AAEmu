[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $root 'upstream-manifest.json') -Raw | ConvertFrom-Json
$upstream = Join-Path $root 'upstream'
foreach ($file in $manifest.files.PSObject.Properties) {
    $path = Join-Path $upstream $file.Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing upstream file: $($file.Name)" }
    # Git's text=auto changes CRLF/LF on Windows; provenance hashes canonical UTF-8/LF.
    $bytes = [Text.Encoding]::UTF8.GetBytes([IO.File]::ReadAllText($path).Replace("`r`n", "`n"))
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '') }
    finally { $sha.Dispose() }
    if ($hash -ne $file.Value) {
        throw "Upstream snapshot changed: $($file.Name). Preserve provenance; review the delta before building."
    }
}
$actual = @(Get-ChildItem -LiteralPath $upstream -Recurse -Force -File)
if ($actual.Count -ne @($manifest.files.PSObject.Properties).Count) {
    throw 'Unmanifested files in upstream snapshot. Keep all build outputs outside upstream/.'
}
Write-Output "Verified $($actual.Count) upstream files at $($manifest.commit)."
