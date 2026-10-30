param(
    [switch]$IncludeLogs,
    [switch]$VerifyForensicsHash
)

$ErrorActionPreference = "Stop"
$projectRoot = "E:\AAEmu\rama_10"
$repo = Join-Path $projectRoot "server\AAEmu"
$parentRef = "upstream/client_version/zone-10.0.2_r575"
$wrongRef = "upstream/client_version/10.0.2_r575"
$client = Join-Path $projectRoot "client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview"
$referenceClient = Join-Path $projectRoot "client\ArcheAge-Returns-10.0.2.13-r575"
$fullDb = Join-Path $projectRoot "data\sqlite\authoritative\game_decrypted.sqlite3"
$compactDb = Join-Path $client "game\db\compact.sqlite3"
$x2game = Join-Path $client "Bin64\x2game.dll"
$forensics = Join-Path $projectRoot "forensics\output\aa10-client-forensics"

if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
    throw "AA10 repository missing: $repo"
}

Write-Output "AAEmu10 status"
Write-Output "project_root=$projectRoot"
Write-Output "primary_client=$client"
Write-Output "reference_client_read_only=$referenceClient"
Write-Output "runtime_locale=en_us"
Write-Output "target_root=$repo"
Write-Output "target_branch=$((git -C $repo branch --show-current).Trim())"
Write-Output "target_head=$((git -C $repo log -1 --format='%H|%s').Trim())"
$dirty = @(git -C $repo status --short | Where-Object { $_ -notmatch ' \.env$' })
Write-Output "target_dirty_non_env=$($dirty.Count)"
$dirty | ForEach-Object { Write-Output "target_dirty:$_" }

Write-Output "origin_url=$((git -C $repo remote get-url origin).Trim())"
Write-Output "upstream_url=$((git -C $repo remote get-url upstream).Trim())"
git -C $repo show-ref --verify --quiet "refs/remotes/$parentRef"
if ($LASTEXITCODE -eq 0) {
    Write-Output "parent_ref=$parentRef"
    Write-Output "parent_head=$((git -C $repo rev-parse $parentRef).Trim())"
    Write-Output "head_parent_divergence=$((git -C $repo rev-list --left-right --count "HEAD...$parentRef").Trim())"
    git -C $repo merge-base --is-ancestor $parentRef HEAD
    Write-Output "parent_is_ancestor=$($LASTEXITCODE -eq 0)"
} else {
    Write-Output "parent_ref_missing=$parentRef"
}
git -C $repo show-ref --verify --quiet "refs/remotes/$wrongRef"
if ($LASTEXITCODE -eq 0) {
    Write-Output "wrong_ref_warning=$wrongRef exists but is not the declared parent"
}

if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    Write-Output "dotnet_sdk=$((dotnet --version).Trim())"
}

foreach ($path in @($fullDb, $compactDb, $x2game)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $item = Get-Item -LiteralPath $path
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        Write-Output ("evidence={0}|bytes={1}|sha256={2}" -f $path,$item.Length,$hash)
    }
}

$forensicsDb = Join-Path $forensics "aa10-client-knowledge.sqlite"
$forensicsManifest = Join-Path $forensics "aa10-client-knowledge.manifest.json"
Write-Output "forensics_output=$forensics"
Write-Output "forensics_database_present=$(Test-Path -LiteralPath $forensicsDb -PathType Leaf)"
if (Test-Path -LiteralPath $forensicsManifest -PathType Leaf) {
    Write-Output "forensics_manifest_sha256=$((Get-FileHash -LiteralPath $forensicsManifest -Algorithm SHA256).Hash)"
    if ($VerifyForensicsHash -and (Test-Path -LiteralPath $forensicsDb -PathType Leaf)) {
        Write-Output "forensics_database_sha256=$((Get-FileHash -LiteralPath $forensicsDb -Algorithm SHA256).Hash)"
    }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    $compose = Join-Path $repo "docker-compose.yaml"
    if (Test-Path -LiteralPath $compose -PathType Leaf) {
        $composeArgs = @("-f", $compose)
        $aa10Override = Join-Path $repo ".server_files\docker-compose.aa10.yaml"
        if (Test-Path -LiteralPath $aa10Override -PathType Leaf) {
            $composeArgs += @("-f", $aa10Override)
        }
        Write-Output "docker_services:"
        & docker compose @composeArgs ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
        if ($IncludeLogs) {
            Write-Output "recent_errors:"
            & docker compose @composeArgs logs --no-color --tail 250 |
                Select-String -Pattern "ERROR|FATAL|Unhandled|serializer size mismatch" |
                Select-Object -Last 50 |
                ForEach-Object { $_.Line }
        }
    }
}
