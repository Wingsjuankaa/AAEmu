[CmdletBinding()]
param(
    [string]$ResearchRoot = "E:\AAEmu-Research",
    [ValidateSet("core", "extended", "all", "verify")]
    [string]$Profile = "core",
    [switch]$Force,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"
$syncMutex = [System.Threading.Mutex]::new($false, "Local\AA8DecompilerToolchainSync")
if (-not $syncMutex.WaitOne(0)) {
    throw "Another AA8 decompiler toolchain sync is already running."
}
$catalogPath = Join-Path $PSScriptRoot "..\config\decompiler-tools.json"
$catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json
$downloadRoot = Join-Path $ResearchRoot "downloads\decompiler-toolchain"
$toolRoot = Join-Path $ResearchRoot "tools"
$manifestRoot = Join-Path $ResearchRoot "output\decompiler-toolchain"
$manifestPath = Join-Path $manifestRoot "installed-tools.json"

foreach ($path in @($ResearchRoot, $downloadRoot, $toolRoot, $manifestRoot)) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

function Resolve-ResearchPath {
    param([Parameter(Mandatory)][string]$RelativePath)
    return [System.IO.Path]::GetFullPath((Join-Path $ResearchRoot $RelativePath))
}

function Assert-InResearchRoot {
    param([Parameter(Mandatory)][string]$Path)
    $resolvedRoot = [System.IO.Path]::GetFullPath($ResearchRoot).TrimEnd("\") + "\"
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside research root: $resolvedPath"
    }
}

function Get-ExpectedExecutable {
    param(
        [Parameter(Mandatory)]$Tool,
        [Parameter(Mandatory)][string]$InstallPath
    )
    if ($Tool.verify_path) {
        return Join-Path $InstallPath $Tool.verify_path
    }
    if ($Tool.verify_glob) {
        return Get-ChildItem -LiteralPath $InstallPath -Recurse -File -Filter $Tool.verify_glob -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
    }
    return $null
}

function Test-PythonImport {
    param(
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][string]$Module
    )
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $PythonPath
    $startInfo.Arguments = "-c `"import $Module`""
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $null = $process.Start()
    $process.WaitForExit()
    return $process.ExitCode -eq 0
}

function Test-ToolInstalled {
    param([Parameter(Mandatory)]$Tool)
    if ($Tool.kind -eq "docker_image") {
        if ($SkipDocker) {
            return $false
        }
        try {
            docker image inspect $Tool.image --format "{{.Id}}" 2>$null | Out-Null
            return $LASTEXITCODE -eq 0
        } catch {
            return $false
        }
    }
    if ($Tool.kind -eq "manual") {
        return $false
    }
    $installPath = Resolve-ResearchPath $Tool.install_path
    if (-not (Test-Path -LiteralPath $installPath)) {
        return $false
    }
    if ($Tool.kind -eq "python_venv") {
        $pythonPath = Join-Path $installPath "venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $pythonPath)) {
            return $false
        }
        return Test-PythonImport -PythonPath $pythonPath -Module $Tool.verify_module
    }
    $expected = Get-ExpectedExecutable -Tool $Tool -InstallPath $installPath
    return $null -ne $expected -and (Test-Path -LiteralPath $expected)
}

function Get-Archive {
    param([Parameter(Mandatory)]$Tool)
    $archivePath = Join-Path $downloadRoot $Tool.asset
    Assert-InResearchRoot $archivePath
    $expectedHash = if ($Tool.sha256) { $Tool.sha256.ToLowerInvariant() } else { $null }
    if (Test-Path -LiteralPath $archivePath) {
        $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if (-not $expectedHash -or $actualHash -eq $expectedHash) {
            return [PSCustomObject]@{ Path = $archivePath; Sha256 = $actualHash }
        }
        if (-not $Force) {
            throw "Hash mismatch for existing archive $archivePath. Use -Force only after reviewing the target."
        }
        Remove-Item -LiteralPath $archivePath -Force
    }
    Invoke-WebRequest -Uri $Tool.download_url -OutFile $archivePath
    $downloadedHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($expectedHash -and $downloadedHash -ne $expectedHash) {
        throw "Publisher hash mismatch for $($Tool.id): expected $expectedHash, got $downloadedHash"
    }
    return [PSCustomObject]@{ Path = $archivePath; Sha256 = $downloadedHash }
}

function Expand-ToolArchive {
    param(
        [Parameter(Mandatory)]$Tool,
        [Parameter(Mandatory)][string]$ArchivePath
    )
    $installPath = Resolve-ResearchPath $Tool.install_path
    Assert-InResearchRoot $installPath
    if (Test-Path -LiteralPath $installPath) {
        if (Test-ToolInstalled $Tool) {
            return $installPath
        }
        if (-not $Force) {
            throw "Incomplete install path already exists: $installPath. Review it or rerun with -Force."
        }
        Remove-Item -LiteralPath $installPath -Recurse -Force
    }
    $parent = Split-Path -Parent $installPath
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    $temporaryPath = "$installPath.partial-$PID"
    Assert-InResearchRoot $temporaryPath
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $temporaryPath | Out-Null
    try {
        if ($Tool.kind -eq "github_7z") {
            & tar.exe -xf $ArchivePath -C $temporaryPath
            if ($LASTEXITCODE -ne 0) {
                throw "tar.exe could not extract $ArchivePath"
            }
        } else {
            Expand-Archive -LiteralPath $ArchivePath -DestinationPath $temporaryPath
        }
        Move-Item -LiteralPath $temporaryPath -Destination $installPath
    } catch {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Recurse -Force
        }
        throw
    }
    return $installPath
}

function Install-PythonTool {
    param([Parameter(Mandatory)]$Tool)
    $installPath = Resolve-ResearchPath $Tool.install_path
    Assert-InResearchRoot $installPath
    $venvPath = Join-Path $installPath "venv"
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"
    if ((Test-Path -LiteralPath $installPath) -and -not (Test-Path -LiteralPath $pythonPath)) {
        if (-not $Force) {
            throw "Incomplete Python tool path already exists: $installPath"
        }
        Remove-Item -LiteralPath $installPath -Recurse -Force
    }
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        & python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create virtual environment for $($Tool.id)"
        }
    }
    $null = & $pythonPath -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to update pip for $($Tool.id)"
    }
    $packages = @($Tool.packages)
    $null = & $pythonPath -m pip install --disable-pip-version-check @packages
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install Python packages for $($Tool.id)"
    }
    if (-not (Test-PythonImport -PythonPath $pythonPath -Module $Tool.verify_module)) {
        throw "Python import verification failed for $($Tool.id)"
    }
    return $installPath
}

$selectedTools = @($catalog.tools | Where-Object {
    if ($Profile -eq "verify") {
        return $_.kind -ne "manual"
    }
    if ($Profile -eq "all") {
        return $_.kind -ne "manual"
    }
    if ($Profile -eq "extended") {
        return $_.profile -in @("core", "extended")
    }
    return $_.profile -eq "core"
})

$results = [System.Collections.Generic.List[object]]::new()
foreach ($tool in $selectedTools) {
    $installedBefore = Test-ToolInstalled $tool
    $archiveHash = $null
    $status = "present"
    $detail = $null
    try {
        if ($Profile -ne "verify" -and -not $installedBefore) {
            switch ($tool.kind) {
                "github_zip" {
                    $archive = Get-Archive $tool
                    $archiveHash = $archive.Sha256
                    $detail = Expand-ToolArchive -Tool $tool -ArchivePath $archive.Path
                    $status = "installed"
                }
                "github_7z" {
                    $archive = Get-Archive $tool
                    $archiveHash = $archive.Sha256
                    $detail = Expand-ToolArchive -Tool $tool -ArchivePath $archive.Path
                    $status = "installed"
                }
                "github_zip_keep" {
                    $archive = Get-Archive $tool
                    $archiveHash = $archive.Sha256
                    $installPath = Resolve-ResearchPath $tool.install_path
                    if (-not (Test-Path -LiteralPath $installPath)) {
                        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
                    }
                    $destination = Join-Path $installPath $tool.asset
                    Copy-Item -LiteralPath $archive.Path -Destination $destination
                    $detail = $destination
                    $status = "installed"
                }
                "python_venv" {
                    $detail = Install-PythonTool $tool
                    $status = "installed"
                }
                "docker_image" {
                    if ($SkipDocker) {
                        $status = "skipped"
                        $detail = "Docker disabled by -SkipDocker"
                    } else {
                        docker pull $tool.image
                        if ($LASTEXITCODE -ne 0) {
                            throw "Docker pull failed for $($tool.image)"
                        }
                        $detail = $tool.image
                        $status = "installed"
                    }
                }
                "existing" {
                    $status = if ($installedBefore) { "present" } else { "missing" }
                }
            }
        } elseif (-not $installedBefore) {
            $status = "missing"
        }
        $installedAfter = Test-ToolInstalled $tool
        if ($status -notin @("skipped", "missing") -and -not $installedAfter) {
            $status = "verification_failed"
        }
    } catch {
        $status = "error"
        $detail = $_.Exception.Message
    }
    $results.Add([PSCustomObject]@{
        id = $tool.id
        version = $tool.version
        profile = $tool.profile
        kind = $tool.kind
        status = $status
        archive_sha256 = $archiveHash
        detail = $detail
        verified_at_utc = [DateTime]::UtcNow.ToString("o")
    })
}

$output = [ordered]@{
    schema = "AA8_DECOMPILER_TOOL_INSTALL_MANIFEST_V1"
    catalog_version = $catalog.catalog_version
    catalog_sha256 = (Get-FileHash -LiteralPath $catalogPath -Algorithm SHA256).Hash.ToLowerInvariant()
    research_root = [System.IO.Path]::GetFullPath($ResearchRoot)
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    profile = $Profile
    tools = $results
}
$output | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$results | Format-Table id, version, profile, status -AutoSize
Write-Output "manifest=$manifestPath"

if ($results.status -contains "error" -or $results.status -contains "verification_failed") {
    $syncMutex.ReleaseMutex()
    $syncMutex.Dispose()
    exit 1
}
$syncMutex.ReleaseMutex()
$syncMutex.Dispose()
