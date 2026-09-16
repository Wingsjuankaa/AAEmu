[CmdletBinding()]
param([string]$ClientRoot, [string]$OutputPath)

# Read-only diagnosis. Never collect process command lines (login token), change
# settings, kill the game, install dependencies or disable security software.
$ErrorActionPreference = 'Stop'
$issues = New-Object 'System.Collections.Generic.List[string]'
$scriptDirectory = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($scriptDirectory)) { $scriptDirectory = (Get-Location).Path }
if ([string]::IsNullOrWhiteSpace($ClientRoot)) { $ClientRoot = $scriptDirectory }
function Read-SafeText([string]$value) {
    (($value -split "`r?`n") | Where-Object {
        $_ -notmatch '(?i)strusertoken|strusername|password|passwd|aaemu-sha256|command.?line|secretkey|authorization:'
    }) -join "`n"
}
function Read-ProcessSample {
    @(Get-CimInstance Win32_Process -Filter "Name='archeage.exe'" -ErrorAction SilentlyContinue |
        Select-Object ProcessId,ExecutablePath,CreationDate,WorkingSetSize,PrivatePageCount,
            KernelModeTime,UserModeTime,ReadTransferCount,WriteTransferCount)
}

function Resolve-DocumentCandidates {
    param([AllowEmptyString()][string]$Reported, [AllowEmptyString()][string]$Unverified,
        [AllowEmptyString()][string]$RegistryPath, [AllowEmptyString()][string]$ProfilePath)
    $candidates = @($Reported, $Unverified, $RegistryPath)
    if (-not [string]::IsNullOrWhiteSpace($ProfilePath)) {
        $candidates += Join-Path $ProfilePath 'Documents'
    }
    # Empty known folders are valid diagnostic evidence, never Join-Path input.
    @($candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        ForEach-Object { [Environment]::ExpandEnvironmentVariables($_) } |
        Select-Object -Unique)
}

$before = @(Read-ProcessSample)
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not (Test-Path -LiteralPath (Join-Path $ClientRoot 'MANIFEST-SHA256.json'))) {
    foreach ($process in $before) {
        if ([string]::IsNullOrWhiteSpace($process.ExecutablePath)) { continue }
        $binPath = Split-Path -Path $process.ExecutablePath -Parent
        if ([string]::IsNullOrWhiteSpace($binPath)) { continue }
        $detectedRoot = Split-Path -Path $binPath -Parent
        if (-not [string]::IsNullOrWhiteSpace($detectedRoot)) { $ClientRoot = $detectedRoot; break }
    }
}
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture,TotalVisibleMemorySize,FreePhysicalMemory
$gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,Status)
$cpu = @(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
$disks = @()
try { $disks = @(Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,HealthStatus) }
catch { $issues.Add('Disk type unavailable.') }

$reportedDocuments = [Environment]::GetFolderPath('MyDocuments')
$unverifiedDocuments = [Environment]::GetFolderPath('MyDocuments', 'DoNotVerify')
$registryDocuments = ''
try {
    $registryDocuments = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name Personal -ErrorAction Stop).Personal
} catch { $issues.Add('Documents registry location unavailable.') }
if ([string]::IsNullOrWhiteSpace($reportedDocuments)) {
    $issues.Add('Windows returned an empty Documents location. Fallback locations are inspected without creating or changing folders.')
}
$documentCandidates = @(Resolve-DocumentCandidates -Reported $reportedDocuments -Unverified $unverifiedDocuments -RegistryPath $registryDocuments -ProfilePath $env:USERPROFILE)
$documentFolders = @($documentCandidates | ForEach-Object { Join-Path $_ 'ArcheAge' })
$documents = [ordered]@{
    reported=$reportedDocuments;unverified=$unverifiedDocuments;registry=$registryDocuments
    candidates=@($documentCandidates | ForEach-Object {
        [ordered]@{path=$_;exists=(Test-Path -LiteralPath $_ -PathType Container)}
    })
}
$files = @()
$manifestPath = Join-Path $ClientRoot 'MANIFEST-SHA256.json'
$manifestMode = 'client_manifest'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    $issues.Add('No client manifest found; using bundled reference for critical files only.')
    $manifestPath = Join-Path $scriptDirectory 'DiagnoseAa10Client.reference.json'
    $manifestMode = 'critical_files_reference'
}
if (Test-Path -LiteralPath $manifestPath) {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $safeRoot = [IO.Path]::GetFullPath($ClientRoot).TrimEnd('\') + '\'
    foreach ($entry in $manifest.files) {
        $target = [IO.Path]::GetFullPath((Join-Path $ClientRoot $entry.path))
        if (-not $target.StartsWith($safeRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path' }
        $exists = $false; $length = $null; $hashOk = $null; $fileError = $null
        try {
        $exists = Test-Path -LiteralPath $target -PathType Leaf
        $length = if ($exists) { (Get-Item -LiteralPath $target).Length } else { $null }
        # Small, critical binaries only. Do not read the entire 86 GiB PAK while loading.
        if ($exists -and $entry.path -match '(?i)(archeage\.exe|x2game\.dll|crysystem\.dll|msvcr100\.dll|msvcp100\.dll)$') {
            $hashOk = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $entry.sha256
        }
        } catch { $fileError = Read-SafeText $_.Exception.Message }
        $files += [ordered]@{path=$entry.path;exists=$exists;bytes=$length;sizeOk=($exists -and $length -eq $entry.bytes);criticalHashOk=$hashOk;error=$fileError}
    }
} else { $issues.Add('No client manifest found. Put this script in the client folder or run with archeage.exe open.') }

$logs = @()
foreach ($directory in (($documentFolders + @($ClientRoot, (Join-Path $ClientRoot 'Bin64'))) | Select-Object -Unique)) {
    if ([string]::IsNullOrWhiteSpace($directory)) { continue }
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) { continue }
    $latest = @(Get-ChildItem -LiteralPath $directory -File -Filter '*.log' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 2)
    foreach ($file in $latest) {
        try {
            $tail = (Get-Content -LiteralPath $file.FullName -Tail 70 -ErrorAction Stop) -join "`n"
            $logs += [ordered]@{path=$file.FullName;modified=$file.LastWriteTime;bytes=$file.Length;tail=(Read-SafeText $tail)}
        } catch {
            $logs += [ordered]@{path=$file.FullName;modified=$file.LastWriteTime;bytes=$file.Length
                attributes=$file.Attributes.ToString();error=(Read-SafeText $_.Exception.Message);hresult=$_.Exception.HResult}
        }
    }
}

$events = @()
try {
    $events = @(Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddHours(-2);Id=1000,1001,1002,33,59} -MaxEvents 100 -ErrorAction Stop |
        Where-Object { $_.Message -match '(?i)archeage|x2game|crysystem' } |
        Select-Object -First 8 TimeCreated,Id,ProviderName,@{Name='Message';Expression={Read-SafeText $_.Message}})
} catch { $issues.Add('No matching Application events, or log unavailable.') }

Write-Host 'Midiendo actividad del proceso durante 10 segundos...'
Start-Sleep -Seconds 10
$after = @(Read-ProcessSample)
$processDetails = @()
foreach ($sample in $after) {
    try {
        $process = Get-Process -Id $sample.ProcessId -ErrorAction Stop
        $modules = @(); $moduleError = $null
        try { $modules = @($process.Modules | Select-Object ModuleName,FileName) }
        catch { $moduleError = Read-SafeText $_.Exception.Message }
        $threads = @($process.Threads | ForEach-Object {
            $reason = $null
            if ($_.ThreadState.ToString() -eq 'Wait') { $reason = $_.WaitReason.ToString() }
            [ordered]@{id=$_.Id;state=$_.ThreadState.ToString();waitReason=$reason}
        })
        $processDetails += [ordered]@{pid=$sample.ProcessId;responding=$process.Responding
            windowTitle=$process.MainWindowTitle;modules=$modules;moduleError=$moduleError;threads=$threads}
    } catch { $issues.Add('Process details: ' + (Read-SafeText $_.Exception.Message)) }
}
$report = [ordered]@{
    schemaVersion=3;generatedAt=(Get-Date).ToString('o');clientRoot=$ClientRoot;documentsLocation=$documents
    administrator=$isAdministrator;manifestMode=$manifestMode;processDetails=$processDetails
    os=$os;gpu=$gpu;cpu=$cpu;disks=$disks;processBefore=$before;processAfter=$after
    files=$files;logs=$logs;applicationEvents=$events;notes=@($issues)
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) { $OutputPath = Join-Path $scriptDirectory ('Diagnostico-AA10-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json') }
$report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Host ('Diagnostico guardado: ' + $OutputPath)
Write-Host 'Envialo para revisar el arranque. No contiene la linea de lanzamiento ni la contrasena.'
