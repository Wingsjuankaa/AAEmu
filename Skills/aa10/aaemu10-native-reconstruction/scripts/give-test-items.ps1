[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Character,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [uint32[]]$ItemId,

    [ValidateRange(1, 1000)]
    [int]$Count = 1,

    [ValidateRange(-1, 12)]
    [int]$Grade = -1,

    [ValidateNotNullOrEmpty()]
    [string]$ContainerName = 'aaemu10-game-1'
)

$ErrorActionPreference = 'Stop'
$apiRoot = 'http://127.0.0.1:1280'

function Invoke-ContainerGetJson {
    param([Parameter(Mandatory = $true)][string]$Url)

    $raw = & docker exec $ContainerName wget -qO- $Url
    if ($LASTEXITCODE -ne 0) {
        throw "GET $Url fallo dentro de $ContainerName (exit=$LASTEXITCODE)."
    }

    try {
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "GET $Url no devolvio JSON valido: $raw"
    }
}

function Invoke-ContainerPostJson {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][object]$Body
    )

    $json = $Body | ConvertTo-Json -Compress
    $raw = & docker exec $ContainerName wget -qO- `
        '--header=Content-Type: application/json' "--post-data=$json" $Url
    if ($LASTEXITCODE -ne 0) {
        throw "POST $Url fallo dentro de $ContainerName (exit=$LASTEXITCODE)."
    }

    try {
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "POST $Url no devolvio JSON valido: $raw"
    }
}

$running = & docker inspect --format '{{.State.Running}}' $ContainerName 2>&1
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') {
    throw "El contenedor $ContainerName no existe o no esta activo."
}

$characters = @(Invoke-ContainerGetJson -Url "$apiRoot/api/world/logged-characters")
$onlineCharacter = $characters | Where-Object {
    $_.IsOnline -and $_.Name -ieq $Character
} | Select-Object -First 1

if ($null -eq $onlineCharacter) {
    $onlineNames = @($characters | Where-Object IsOnline | ForEach-Object Name)
    throw "El personaje '$Character' no esta online. Online: $($onlineNames -join ', ')."
}

$seen = [System.Collections.Generic.HashSet[uint32]]::new()
foreach ($id in $ItemId) {
    if (-not $seen.Add($id)) {
        continue
    }

    $gradeDescription = if ($Grade -ge 0) { " grade $Grade" } else { '' }
    $description = "$Count x item template $id$gradeDescription -> $($onlineCharacter.Name)"
    if (-not $PSCmdlet.ShouldProcess($ContainerName, $description)) {
        continue
    }

    $arguments = "add self $id $Count"
    if ($Grade -ge 0) {
        $arguments += " $Grade"
    }

    $response = Invoke-ContainerPostJson -Url "$apiRoot/api/commands/item" -Body ([ordered]@{
        character = $onlineCharacter.Name
        arguments = $arguments
    })

    $errors = @($response.ErrorMessages | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $failureMessages = @($response.Messages | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_) -and (
            $_ -match '\|cFFFF0000' -or
            $_ -match '(?i)insufficient privileges|invalid|not found|cannot|full|failed|error'
        )
    })
    $failures = @($errors) + @($failureMessages)
    if ($failures.Count -gt 0) {
        throw "Fallo item template $id; se detuvo el lote: $($failures -join ' | ')"
    }

    [pscustomobject]@{
        Character = $onlineCharacter.Name
        ItemId = $id
        Count = $Count
        Grade = if ($Grade -ge 0) { $Grade } else { 'Default' }
        CommandLine = $response.commandLine
        Status = 'Delivered'
    }
}
