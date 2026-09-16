[CmdletBinding(DefaultParameterSetName = 'Character')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Character')][ValidatePattern('^[\p{L}\p{N}_-]{1,32}$')][string]$Character,
    [Parameter(Mandatory, ParameterSetName = 'Account')][ValidateLength(1,32)][string]$Account,
    [ValidateSet('Grant', 'Revoke')][string]$Action = 'Grant',
    [string]$DatabaseContainer = 'aaemu10-db-1'
)
$ErrorActionPreference = 'Stop'
# Only authorization is written. Account grants cover existing and future characters.
# Inventory and GM privileges are never changed by this script.
$isAccount = $PSCmdlet.ParameterSetName -eq 'Account'
$targetName = if ($isAccount) { $Account } else { $Character }
# Encode the name as a UTF-8 SQL literal (including quotes/non-ASCII safely).
$hexName = [BitConverter]::ToString([Text.Encoding]::UTF8.GetBytes($targetName)).Replace('-', '')
$sqlName = "CONVERT(0x$hexName USING utf8mb4)"
$query = if ($isAccount) {
    "SELECT id FROM aaemu_login.users WHERE LOWER(username)=LOWER($sqlName);"
} else {
    "SELECT id FROM characters WHERE deleted=0 AND LOWER(name)=LOWER($sqlName);"
}
$sqlCommand = 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -N --default-character-set=utf8mb4 aaemu_game'
$matches = @($query | docker exec -i $DatabaseContainer sh -c $sqlCommand)
if ($LASTEXITCODE -ne 0 -or $matches.Count -ne 1) { throw 'Expected exactly one existing account or active character.' }
$targetId = [uint32]$matches[0]
$table = if ($isAccount) { 'private_alpha_account_access' } else { 'private_alpha_access' }
$column = if ($isAccount) { 'account_id' } else { 'character_id' }
$sql = if ($Action -eq 'Grant') {
    "INSERT INTO $table ($column,granted_by,granted_at) VALUES ($targetId,0,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE $column=$column;"
} else {
    "DELETE FROM $table WHERE $column=$targetId;"
}
$sql | docker exec -i $DatabaseContainer sh -c $sqlCommand
if ($LASTEXITCODE -ne 0) { throw 'Private alpha authorization update failed.' }
"$Action applied: $($PSCmdlet.ParameterSetName) '$targetName' (id=$targetId)."
if ($isAccount) {
    'The account permission covers all current and future characters. Independent character grants remain in effect after account revocation.'
} else {
    'Only the individual permission changed. An account grant still permits access after individual revocation.'
}
'Game checks permission on every operation. The HUD refreshes within 30 seconds; the optional key is delivered on the next world entry.'
