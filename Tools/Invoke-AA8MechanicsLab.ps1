param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('run', 'analyze-trace', 'import-trace')]
    [string]$Command,
    [string]$Scenario,
    [string]$Compact,
    [string]$Trace,
    [string]$Fixture,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = if ($Command -eq 'run') {
        'runtime-captures/mechanics-lab'
    } else {
        "runtime-captures/mechanics-lab/$Command.json"
    }
}
function Convert-ToContainerInputPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    $absolute = (Resolve-Path $Path).Path
    if ($absolute.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)) {
        return '/src/' + $absolute.Substring($repo.Length).TrimStart('\').Replace('\', '/')
    }
    throw "Path must be inside the repository for the Docker wrapper: $absolute"
}

function Convert-ToContainerOutputPath([string]$Path) {
    $absolute = [System.IO.Path]::GetFullPath((Join-Path $repo $Path))
    if (-not $absolute.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Output must be inside the repository: $absolute"
    }
    $parent = if ($Command -eq 'run') { $absolute } else { Split-Path -Parent $absolute }
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    return '/src/' + $absolute.Substring($repo.Length).TrimStart('\').Replace('\', '/')
}

$dockerArguments = @('run', '--rm', '-v', "${repo}:/src")
if ($Compact) {
    $compactPath = (Resolve-Path $Compact).Path
    $dockerArguments += @('-v', "${compactPath}:/compact.sqlite3:ro")
}
$dockerArguments += @('-w', '/src', 'mcr.microsoft.com/dotnet/sdk:3.1.409-focal',
    'dotnet', 'run', '--project', './AAEmu.MechanicsLab.Cli/AAEmu.MechanicsLab.Cli.csproj', '--', $Command)

if ($Scenario) { $dockerArguments += @('--scenario', (Convert-ToContainerInputPath $Scenario)) }
if ($Compact) {
    $dockerArguments += @('--compact', '/compact.sqlite3')
}
if ($Trace) { $dockerArguments += @('--trace', (Convert-ToContainerInputPath $Trace)) }
if ($Fixture) { $dockerArguments += @('--fixture', (Convert-ToContainerInputPath $Fixture)) }
$dockerArguments += @('--output', (Convert-ToContainerOutputPath $Output))

& docker @dockerArguments
exit $LASTEXITCODE
