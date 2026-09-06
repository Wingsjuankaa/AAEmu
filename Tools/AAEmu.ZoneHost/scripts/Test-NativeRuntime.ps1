[CmdletBinding()]
param(
    [string]$BinDirectory = 'E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64',
    [string]$ReportPath
)
$ErrorActionPreference = 'Stop'
# Read PE bytes only. Never LoadLibrary: DLL entry points must not run during this audit.
function Read-Pe([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 256 -or [BitConverter]::ToUInt16($bytes, 0) -ne 0x5A4D) { throw "Invalid DOS header: $Path" }
    $pe = [BitConverter]::ToInt32($bytes, 0x3c)
    if ($pe -lt 0 -or $pe + 264 -gt $bytes.Length -or [BitConverter]::ToUInt32($bytes, $pe) -ne 0x4550) { throw "Invalid PE: $Path" }
    if ([BitConverter]::ToUInt16($bytes, $pe + 4) -ne 0x8664 -or [BitConverter]::ToUInt16($bytes, $pe + 24) -ne 0x20b) { throw "Expected Windows x64 PE32+: $Path" }
    $sections = @()
    $count = [BitConverter]::ToUInt16($bytes, $pe + 6)
    $optionalSize = [BitConverter]::ToUInt16($bytes, $pe + 20)
    for ($index = 0; $index -lt $count; $index++) {
        $offset = $pe + 24 + $optionalSize + $index * 40
        if ($offset + 40 -gt $bytes.Length) { throw 'Truncated PE section table.' }
        $sections += [pscustomobject]@{
            rva = [BitConverter]::ToUInt32($bytes, $offset + 12)
            size = [BitConverter]::ToUInt32($bytes, $offset + 16)
            raw = [BitConverter]::ToUInt32($bytes, $offset + 20)
        }
    }
    return [pscustomobject]@{bytes=$bytes; pe=$pe; sections=$sections; imageBase=[BitConverter]::ToUInt64($bytes, $pe + 48)}
}
function Get-Offset($Image, [uint32]$Rva, [int]$Length = 1) {
    foreach ($section in $Image.sections) {
        if ($Rva -ge $section.rva -and [uint64]$Rva + $Length -le [uint64]$section.rva + $section.size) {
            $offset = [long]$section.raw + $Rva - $section.rva
            if ($offset + $Length -gt $Image.bytes.Length) { throw 'PE range exceeds file.' }
            return [int]$offset
        }
    }
    throw ('RVA 0x{0:X} is not file-backed.' -f $Rva)
}
function Read-AsciiZ($Image, [uint32]$Rva) {
    $offset = Get-Offset $Image $Rva
    $end = $offset
    while ($end -lt $Image.bytes.Length -and $Image.bytes[$end] -ne 0) { $end++ }
    if ($end -eq $Image.bytes.Length) { throw 'Unterminated PE string.' }
    return [Text.Encoding]::ASCII.GetString($Image.bytes, $offset, $end - $offset)
}
function Get-Imports($Image) {
    $rva = [BitConverter]::ToUInt32($Image.bytes, $Image.pe + 24 + 120)
    if ($rva -eq 0) { return }
    for ($index = 0; $index -lt 4096; $index++) {
        $offset = Get-Offset $Image ($rva + $index * 20) 20
        $nameRva = [BitConverter]::ToUInt32($Image.bytes, $offset + 12)
        if ($nameRva -eq 0) { return }
        Read-AsciiZ $Image $nameRva
    }
    throw 'PE import count exceeds audit bound.'
}
function Get-ExportRva($Image, [string]$Name) {
    $rva = [BitConverter]::ToUInt32($Image.bytes, $Image.pe + 24 + 112)
    $offset = Get-Offset $Image $rva 40
    $count = [BitConverter]::ToUInt32($Image.bytes, $offset + 24)
    $functions = [BitConverter]::ToUInt32($Image.bytes, $offset + 28)
    $names = [BitConverter]::ToUInt32($Image.bytes, $offset + 32)
    $ordinals = [BitConverter]::ToUInt32($Image.bytes, $offset + 36)
    for ($index = 0; $index -lt $count; $index++) {
        $nameRva = [BitConverter]::ToUInt32($Image.bytes, (Get-Offset $Image ($names + $index * 4) 4))
        if ((Read-AsciiZ $Image $nameRva) -ceq $Name) {
            $ordinal = [BitConverter]::ToUInt16($Image.bytes, (Get-Offset $Image ($ordinals + $index * 2) 2))
            return [BitConverter]::ToUInt32($Image.bytes, (Get-Offset $Image ($functions + $ordinal * 4) 4))
        }
    }
    return $null
}
$dllPath = Join-Path $BinDirectory 'x2game-dev_dedicate.dll'
$dll = Read-Pe $dllPath
$checks = @()
foreach ($probe in @(
    @{name='ship hook';rva=0x360862;expected='48-8B-15-4F-87-2D-01'},
    @{name='model lookup';rva=0x258830;expected='48-8B-81-48-85-00-00-C3'},
    @{name='physicalization virtual';rva=0x289AC0;expected='48-89-5C-24-08-57-48-83-EC-20-48-8B-F9-48-8B-89-60-03-00-00'},
    @{name='unused cave';rva=0xE76C80;expected=((@('CC') * 128) -join '-')}
)) {
    $length = $probe.expected.Split('-').Length
    $actual = [BitConverter]::ToString($dll.bytes, (Get-Offset $dll $probe.rva $length), $length)
    $checks += [pscustomobject]@{name=$probe.name;rva=('0x{0:X}' -f $probe.rva);matches=($actual -eq $probe.expected);actual=$actual}
}
$virtual = [BitConverter]::ToUInt64($dll.bytes, (Get-Offset $dll 0xFC6160 8)) - $dll.imageBase
$checks += [pscustomobject]@{name='ShipUnitModel vtable slot';rva='0xFC6160';matches=($virtual -eq 0x289AC0);actual=('module+0x{0:X}' -f $virtual)}
$cry = Read-Pe (Join-Path $BinDirectory 'CrySystem.dll')
$prompt = Get-ExportRva $cry '?Prompt@CUNIXConsole@@QEAADPEBD0@Z'
$checks += [pscustomobject]@{name='CrySystem Prompt export';rva='0xAB1C0';matches=($prompt -eq 0xAB1C0);actual=('0x{0:X}' -f $prompt)}
$binaries = @()
foreach ($name in @('AAEmu.ZoneHost.exe','x2game-dev_dedicate.dll','CrySystem.dll','xlcommon.dll')) {
    $path = Join-Path $BinDirectory $name
    $image = Read-Pe $path
    $binaries += [pscustomobject]@{name=$name;sha256=(Get-FileHash -LiteralPath $path).Hash;imports=@(Get-Imports $image)}
}
$engine = 'unavailable'
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $engineOutput = & docker info --format '{{.OSType}}' 2>$null
    if ($LASTEXITCODE -eq 0) { $engine = "$engineOutput".Trim() }
}
$report = [ordered]@{
    inspectedAtUtc=[DateTime]::UtcNow.ToString('o')
    binDirectory=$BinDirectory
    binaries=$binaries
    staticChecks=$checks
    matchesUnpatchedShipSitesAndConsoleExport=(@($checks | Where-Object { -not $_.matches }).Count -eq 0)
    dockerEngine=$engine
    nativeWindowsContainerEngineAvailable=($engine -eq 'windows')
    runtimeExecuted=$false
    scope='Static PE audit only; not full ABI compatibility, transitive dependency closure, or gameplay acceptance. Already-patched DLLs require a separate exact-stub audit.'
}
$json = $report | ConvertTo-Json -Depth 7
if ($ReportPath) {
    New-Item -ItemType Directory -Path (Split-Path -Parent ([IO.Path]::GetFullPath($ReportPath))) -Force | Out-Null
    $json | Set-Content -LiteralPath $ReportPath -Encoding utf8
}
$json
