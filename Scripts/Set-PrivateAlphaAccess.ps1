[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[\p{L}\p{N}_-]{1,32}$')][string]$Character,
    [ValidateSet('Grant', 'Revoke')][string]$Action = 'Grant',
    [string]$DatabaseContainer = 'aaemu10-db-1'
)
$ErrorActionPreference = 'Stop'
# Only authorization is written. The Game login hook delivers the item through
# its persisted inventory lifecycle; this script never inserts inventory rows.
$query = "SELECT id,name FROM characters WHERE LOWER(name)=LOWER('$Character');"
$sqlCommand = 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -N --default-character-set=utf8mb4 aaemu_game'
$matches = @($query | docker exec -i $DatabaseContainer sh -c $sqlCommand)
if ($LASTEXITCODE -ne 0 -or $matches.Count -ne 1) { throw 'Expected exactly one existing character.' }
$characterId = [uint32]($matches[0] -split "`t")[0]
$sql = if ($Action -eq 'Grant') {
    "INSERT INTO private_alpha_access (character_id,granted_by,granted_at) VALUES ($characterId,0,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE character_id=character_id;"
} else {
    "DELETE FROM private_alpha_access WHERE character_id=$characterId;"
}
$sql | docker exec -i $DatabaseContainer sh -c $sqlCommand
if ($LASTEXITCODE -ne 0) { throw 'Private alpha authorization update failed.' }
"$Action applied: $Character (id=$characterId). Grant delivers the key on the next world entry; revoke is immediate."
