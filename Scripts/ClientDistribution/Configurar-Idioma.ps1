[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference = 'Stop'

function Set-SpanishLocaleBytes {
    param([byte[]]$Bytes)
    # Preserve existing encoding, BOM, line endings and all unrelated settings.
    $offset = 0
    $encoding = [Text.Encoding]::GetEncoding(28591)
    if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 239 -and $Bytes[1] -eq 187 -and $Bytes[2] -eq 191) {
        $encoding = New-Object Text.UTF8Encoding($false, $true); $offset = 3
    } elseif ($Bytes.Length -ge 2 -and $Bytes[0] -eq 255 -and $Bytes[1] -eq 254) {
        $encoding = [Text.Encoding]::Unicode; $offset = 2
    } elseif ($Bytes.Length -ge 2 -and $Bytes[0] -eq 254 -and $Bytes[1] -eq 255) {
        $encoding = [Text.Encoding]::BigEndianUnicode; $offset = 2
    }
    $text = $encoding.GetString($Bytes, $offset, $Bytes.Length - $offset)
    $pattern = '(?im)^[\t ]*locale[\t ]*=[^\r\n]*'
    if ([regex]::IsMatch($text, $pattern)) {
        $text = [regex]::Replace($text, $pattern, 'locale = en_us')
    } else {
        $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
        if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += $newline }
        $text += 'locale = en_us' + $newline
    }
    $prefix = if ($offset) { [byte[]]$Bytes[0..($offset-1)] } else { [byte[]]@() }
    return ,([byte[]]($prefix + $encoding.GetBytes($text)))
}

$documents = [Environment]::GetFolderPath('MyDocuments')
if ([string]::IsNullOrWhiteSpace($documents)) { throw 'Windows no devuelve Documentos. Revisa primero OneDrive.' }
$folder = Join-Path $documents 'ArcheAge'
$configPath = Join-Path $folder 'system.cfg'
Write-Host ('Configuracion del usuario: ' + $configPath)
if ($Apply -and @(Get-Process -Name archeage -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Cierra el juego antes de aplicar el idioma para que no sobrescriba el cambio al salir.'
}
$exists = Test-Path -LiteralPath $configPath -PathType Leaf
$before = if ($exists) { [IO.File]::ReadAllBytes($configPath) } else { [byte[]]@() }
$after = Set-SpanishLocaleBytes -Bytes $before
if ([Convert]::ToBase64String($before) -eq [Convert]::ToBase64String($after)) {
    Write-Host 'Ya tiene locale = en_us. Si el juego sigue en chino, envia el diagnostico del launcher para comprobar perfil y paquete.'
    exit 0
}
if (-not $Apply) { Write-Host 'Cambio pendiente: locale = en_us. Ejecuta Configurar idioma espanol.cmd para aplicarlo.'; exit 0 }
[IO.Directory]::CreateDirectory($folder) | Out-Null
$temporary = $configPath + '.aa10-' + [guid]::NewGuid().ToString('N') + '.tmp'
[IO.File]::WriteAllBytes($temporary, $after)
if ($exists) {
    $backup = $configPath + '.antes-idioma-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff') + '.bak'
    [IO.File]::Replace($temporary, $configPath, $backup)
    Write-Host ('Respaldo: ' + $backup)
} else { [IO.File]::Move($temporary, $configPath) }
if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($configPath)) -ne [Convert]::ToBase64String($after)) {
    throw 'La verificacion del archivo guardado fallo.'
}
Write-Host 'Guardado y verificado: locale = en_us. Abre el juego desde el launcher LAN.'
Write-Host 'en_us es el canal interno utilizado por la traduccion espanola de esta distribucion.'
