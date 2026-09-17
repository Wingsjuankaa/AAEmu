[CmdletBinding()]
param(
    [ValidateSet('Inspect','Apply','Rollback')][string]$Mode = 'Inspect',
    [string]$ClientRoot,
    [switch]$SkipProfileInitialization,
    [switch]$NoDistributionManifest
)
$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 -File can bind parameter defaults before PSScriptRoot is set.
# Resolve the default here, where the script's own directory is available.
if (-not $PSBoundParameters.ContainsKey('ClientRoot')) { $ClientRoot = $PSScriptRoot }
if ([string]::IsNullOrWhiteSpace($ClientRoot)) {
    throw 'No se pudo resolver la carpeta del cliente. Extrae el paquete completo junto a Jugar en LAN.cmd.'
}
# This process uses only Windows' built-in modules, never modules in cloud-backed Documents.
$env:PSModulePath = [Environment]::GetFolderPath('System') + '\WindowsPowerShell\v1.0\Modules'
$beforeHash = 'D81BA53E5DF0DC6B5031D3D423A6A2720288D6CA40BE0768AAE85E2F30EA4113'
$afterHash = '513CBCE7C62C734B504ADEB0BF7BB7E52FEAC74166EC67B131A322BE4BD8E565'
$exeHash = '6DF26B74D545313C4E6C3EA195DDABCC0CCED7AA8035986EFD6C31B075A4C248'
$patchOffset = 0x1b121
$beforeCode = '4533c9488d8424d00400004533c0418d510533c94889442420'
$afterCode = '6a014159488d8424d00400004533c06a055a33c94889442420'

function Get-BytesHash([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','') }
    finally { $sha.Dispose() }
}
function Convert-HexBytes([string]$Hex) {
    return ,([byte[]]@(for ($i=0; $i -lt $Hex.Length; $i+=2) { [Convert]::ToByte($Hex.Substring($i,2),16) }))
}
function Assert-LocalPath([string]$Path) {
    $candidate = [IO.Path]::GetFullPath($Path)
    if ($candidate.StartsWith('\\')) { throw 'La carpeta local no puede estar en una ruta de red.' }
    foreach ($cloudRoot in @($env:OneDrive,$env:OneDriveConsumer,$env:OneDriveCommercial)) {
        if (-not [string]::IsNullOrWhiteSpace($cloudRoot)) {
            $cloud = [IO.Path]::GetFullPath($cloudRoot).TrimEnd('\')
            if ($candidate.Equals($cloud,[StringComparison]::OrdinalIgnoreCase) -or
                $candidate.StartsWith($cloud+'\',[StringComparison]::OrdinalIgnoreCase)) {
                throw 'La carpeta predeterminada sigue dentro de OneDrive. No se aplico el parche.'
            }
        }
    }
    while (-not [string]::IsNullOrWhiteSpace($candidate)) {
        # GetAttributes examines the directory entry without enumerating cloud files.
        if ([IO.Directory]::Exists($candidate) -or [IO.File]::Exists($candidate)) {
            if (([IO.File]::GetAttributes($candidate) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw ('La ruta contiene una redireccion: '+$candidate)
            }
        }
        $candidate = [IO.Path]::GetDirectoryName($candidate)
    }
}
function Get-DefaultDocuments {
    if (-not ('Aa10DefaultDocuments' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class Aa10DefaultDocuments {
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)]
    public static extern int SHGetFolderPathW(IntPtr hwnd, int csidl, IntPtr token, uint flags, StringBuilder path);
}
'@
    }
    $path = New-Object Text.StringBuilder 260
    # PERSONAL | DONT_VERIFY, DEFAULT: obtain the unredirected location even on a new profile.
    $result = [Aa10DefaultDocuments]::SHGetFolderPathW([IntPtr]::Zero,0x4005,[IntPtr]::Zero,1,$path)
    if ($result -ne 0 -or $path.Length -eq 0) { throw 'Windows no pudo resolver Documentos local.' }
    Assert-LocalPath $path.ToString()
    return $path.ToString()
}
function Write-Atomic([string]$Path,[byte[]]$Bytes) {
    $temporary = $Path + '.aa10-' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllBytes($temporary,$Bytes)
        if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temporary,$Path,[NullString]::Value) }
        else { [IO.File]::Move($temporary,$Path) }
        if ((Get-BytesHash ([IO.File]::ReadAllBytes($Path))) -ne (Get-BytesHash $Bytes)) {
            throw ('Fallo de verificacion: '+$Path)
        }
    } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
}

$ClientRoot = [IO.Path]::GetFullPath($ClientRoot)
$dllPath = Join-Path $ClientRoot 'Bin64\xlcommon.dll'
$exePath = Join-Path $ClientRoot 'Bin64\archeage.exe'
Assert-LocalPath $dllPath
Assert-LocalPath $exePath
if ((Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash -ne $exeHash) {
    throw 'archeage.exe no corresponde al cliente AA10 r575 aprobado.'
}
$original = [IO.File]::ReadAllBytes($dllPath)
$currentHash = Get-BytesHash $original
if ($currentHash -notin @($beforeHash,$afterHash)) { throw 'xlcommon.dll tiene una version desconocida. No se modifico.' }
$desiredHash = if ($Mode -eq 'Rollback') { $beforeHash } else { $afterHash }
$desiredCode = Convert-HexBytes $(if ($Mode -eq 'Rollback') { $beforeCode } else { $afterCode })
$patched = [byte[]]$original.Clone()
[Array]::Copy($desiredCode,0,$patched,$patchOffset,$desiredCode.Length)
if ((Get-BytesHash $patched) -ne $desiredHash) { throw 'El resultado del parche no coincide con su hash aprobado.' }

$profilePath = $null
if (-not $SkipProfileInitialization -and $Mode -ne 'Rollback') {
    $profilePath = Join-Path (Get-DefaultDocuments) 'ArcheAge'
    Assert-LocalPath $profilePath
    if (($profilePath.Length + 1) -ge 260) { throw 'La ruta excede el limite nativo del cliente.' }
    Write-Host ('Perfil local: '+$profilePath)
}

$manifestPath = Join-Path $ClientRoot 'MANIFEST-SHA256.json'
$manifestBefore = $null
$manifestAfter = $null
if (-not $NoDistributionManifest) {
    $baselinePath = Join-Path $PSScriptRoot 'MANIFEST-SHA256.original.json'
    $baseline = [IO.File]::ReadAllBytes($baselinePath)
    if ((Get-BytesHash $baseline) -ne 'EEC86FAE1BE0629372D7FB235A7A16290B507B1EA6CB4DC6F6BFA3F90371C56B') {
        throw 'El manifiesto original incluido no es el aprobado.'
    }
    $obj = [Text.Encoding]::UTF8.GetString($baseline) | ConvertFrom-Json
    $entry = @($obj.files | Where-Object { $_.path.Replace('\','/') -eq 'Bin64/xlcommon.dll' })
    if ($entry.Count -ne 1) { throw 'Entrada xlcommon.dll ambigua en el manifiesto.' }
    $entry[0].sha256 = $afterHash
    $obj.build = 'AA10-Nuia-Alpha-es_ES-LAN-20260915-PerfilLocal-20260916'
    $obj.all_destination_hashes_verified = $false
    $obj | Add-Member -NotePropertyName client_patch -NotePropertyValue 'local-documents-v1; run Verificar cliente.cmd on this PC'
    $utf8 = New-Object Text.UTF8Encoding($false)
    $updated = $utf8.GetBytes(($obj | ConvertTo-Json -Depth 20) + "`n")
    if ([IO.File]::Exists($manifestPath)) {
        $manifestBefore = [IO.File]::ReadAllBytes($manifestPath)
        if ((Get-BytesHash $manifestBefore) -notin @((Get-BytesHash $baseline),(Get-BytesHash $updated))) {
            throw 'El manifiesto del cliente tiene otros cambios. Se requiere revisar esa version.'
        }
    }
    $manifestAfter = if ($Mode -eq 'Rollback') { $baseline } else { $updated }
}
Write-Host ('Estado DLL: '+$(if ($currentHash -eq $afterHash) { 'perfil local activo' } else { 'perfil original' }))
if ($Mode -eq 'Inspect') { Write-Host 'Inspeccion terminada; no se modificaron archivos.'; exit 0 }
foreach ($process in @(Get-CimInstance Win32_Process -Filter "Name='archeage.exe'")) {
    if ([string]::IsNullOrWhiteSpace($process.ExecutablePath) -or
        $process.ExecutablePath.Equals($exePath,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Cierra esta copia del juego antes de aplicar o revertir el parche.'
    }
}

$backupRoot = Join-Path $ClientRoot '.aa10-local-profile-backup'
Assert-LocalPath $backupRoot
[IO.Directory]::CreateDirectory($backupRoot) | Out-Null
$dllBackup = Join-Path $backupRoot ($currentHash + '.xlcommon.dll')
if (-not [IO.File]::Exists($dllBackup)) { [IO.File]::WriteAllBytes($dllBackup,$original) }
if ((Get-FileHash -LiteralPath $dllBackup -Algorithm SHA256).Hash -ne $currentHash) { throw 'Respaldo DLL invalido.' }
if ($null -ne $manifestBefore) {
    [IO.File]::WriteAllBytes((Join-Path $backupRoot ((Get-BytesHash $manifestBefore)+'.manifest.json')),$manifestBefore)
}
if ($profilePath) {
    [IO.Directory]::CreateDirectory($profilePath) | Out-Null
    $configPath = Join-Path $profilePath 'system.cfg'
    Assert-LocalPath $configPath
    # No cloud migration: retain an existing local profile and create only the minimum for a new one.
    if (-not [IO.File]::Exists($configPath)) {
        Write-Atomic $configPath ([Text.Encoding]::ASCII.GetBytes("locale = en_us`r`n"))
    }
    $probe = Join-Path $profilePath ('.aa10-write-probe-'+[guid]::NewGuid().ToString('N'))
    try { [IO.File]::WriteAllText($probe,'ok') } finally { if ([IO.File]::Exists($probe)) { [IO.File]::Delete($probe) } }
}
try {
    if ($currentHash -ne $desiredHash) { Write-Atomic $dllPath $patched }
    if ($null -ne $manifestAfter) { Write-Atomic $manifestPath $manifestAfter }
} catch {
    Write-Atomic $dllPath $original
    if ($null -ne $manifestBefore) { Write-Atomic $manifestPath $manifestBefore }
    elseif ([IO.File]::Exists($manifestPath)) { [IO.File]::Delete($manifestPath) }
    throw
}
Write-Host ('OK: '+$(if ($Mode -eq 'Rollback') { 'restaurado el comportamiento original. Se conserva el perfil local.' } else { 'cliente configurado para Documentos local.' }))
if ($profilePath) { Write-Host ('Configuracion y logs: '+$profilePath) }
Write-Host 'Abre el juego con tu launcher habitual.'
