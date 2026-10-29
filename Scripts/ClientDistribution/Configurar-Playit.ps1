param(
    [string]$ClientRoot = $PSScriptRoot,
    [string]$LoginHost = 'laurel-filmed.tun.ply.gg',
    [ValidateRange(1, 65535)][int]$LoginPort = 49172
)
$ErrorActionPreference = 'Stop'
$clientExe = Join-Path $ClientRoot 'Bin64/archeage.exe'
if (-not (Test-Path -LiteralPath $clientExe -PathType Leaf)) {
    throw 'Coloca estos archivos en la carpeta del cliente, junto al launcher y game_pak.'
}
if (Get-Process -Name 'AAEmu-Simple-Launcher*' -ErrorAction SilentlyContinue) {
    throw 'Cierra el launcher antes de configurar el perfil de Internet.'
}
$profileDirectory = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'aaemu-simple-launcher'
New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
$profilePath = Join-Path $profileDirectory 'profiles.json'
$now = [DateTime]::UtcNow.ToString('o')
if (Test-Path -LiteralPath $profilePath) {
    $collection = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
    if ($collection.schemaVersion -ne 1 -or $null -eq $collection.profiles) {
        throw 'Formato de perfiles no reconocido. No se ha modificado.'
    }
    Copy-Item -LiteralPath $profilePath -Destination "$profilePath.before-playit-$(Get-Date -Format yyyyMMdd-HHmmss-fff)"
} else {
    $collection = [pscustomobject]@{ schemaVersion = 1; activeProfileId = 'aa10-playit'; profiles = @() }
}
$profile = [pscustomobject]@{
    schemaVersion = 1; id = 'aa10-playit'; name = 'AA10 Alpha Internet'
    clientExe = [IO.Path]::GetFullPath($clientExe)
    loginHost = $LoginHost; loginPort = $LoginPort; gameId = 1
    locale = 'en_us'; worldMode = 'normal'; createdAt = $now; updatedAt = $now
}
$existing = @($collection.profiles | Where-Object id -eq 'aa10-playit')
if ($existing.Count -gt 0) { $profile.createdAt = $existing[0].createdAt }
$collection.profiles = @($collection.profiles | Where-Object id -ne 'aa10-playit') + $profile
$collection.activeProfileId = $profile.id
$tempPath = "$profilePath.playit.tmp"
[IO.File]::WriteAllText($tempPath, ($collection | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $tempPath -Destination $profilePath -Force
Write-Host "Perfil AA10 Alpha Internet configurado: ${LoginHost}:$LoginPort"
