param([switch]$HashGamePak)

$ErrorActionPreference = "Stop"
$projectRoot = "E:\AAEmu\rama_10"
$repo = Join-Path $projectRoot "server\AAEmu"
$client = Join-Path $projectRoot "client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview"
$referenceClient = Join-Path $projectRoot "client\ArcheAge-Returns-10.0.2.13-r575"
$fullDb = Join-Path $projectRoot "data\sqlite\authoritative\game_decrypted.sqlite3"
$compactDb = Join-Path $client "game\db\compact.sqlite3"
$x2game = Join-Path $client "Bin64\x2game.dll"
$gamePak = Join-Path $client "game_pak"
$output = Join-Path $projectRoot "forensics\output\aa10-client-forensics"
$state = Join-Path (Split-Path -Parent $PSScriptRoot) "references\current-forensic-state.md"
$parentRef = "upstream/client_version/zone-10.0.2_r575"

Write-Output "AA10 client forensics status"
Write-Output "project_root=$projectRoot"
Write-Output "primary_client=$client"
Write-Output "reference_client_read_only=$referenceClient"
Write-Output "primary_evidence_role=localized_patched_client_observed"
Write-Output "mode=forensics_only"
Write-Output "server_mutation=forbidden"
Write-Output "repo=$repo"
git -C $repo branch --show-current
git -C $repo log -1 --format="%H|%s"
git -C $repo show-ref --verify --quiet "refs/remotes/$parentRef"
if ($LASTEXITCODE -eq 0) {
    $counts = (git -C $repo rev-list --left-right --count "HEAD...$parentRef").Trim()
    Write-Output "parent_ref=$parentRef"
    Write-Output "head_parent_divergence=$counts"
} else {
    Write-Output "parent_ref_missing=$parentRef"
}

foreach ($path in @($fullDb, $compactDb, $x2game)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $item = Get-Item -LiteralPath $path
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        Write-Output ("artifact={0}|bytes={1}|sha256={2}" -f $path,$item.Length,$hash)
    } else {
        Write-Output "artifact_missing=$path"
    }
}

if (Test-Path -LiteralPath $gamePak -PathType Leaf) {
    $item = Get-Item -LiteralPath $gamePak
    Write-Output ("game_pak={0}|bytes={1}|mtime={2:o}" -f $gamePak,$item.Length,$item.LastWriteTimeUtc)
    if ($HashGamePak) {
        Write-Output "game_pak_sha256=$((Get-FileHash -LiteralPath $gamePak -Algorithm SHA256).Hash)"
    }
}

Write-Output "forensics_output=$output"
Write-Output "consolidated_present=$(Test-Path -LiteralPath (Join-Path $output 'aa10-client-knowledge.sqlite'))"
if (Test-Path -LiteralPath $state -PathType Leaf) {
    Write-Output "continuity_state=$state|sha256=$((Get-FileHash -LiteralPath $state -Algorithm SHA256).Hash)"
}
