$ErrorActionPreference = 'Stop'
$lanAddress = '192.168.100.20'
$lanFailures = 0
foreach ($lanPort in @(1237, 1239, 1250)) {
    $lanSocket = New-Object System.Net.Sockets.TcpClient
    try {
        $lanAttempt = $lanSocket.ConnectAsync($lanAddress, $lanPort)
        if (-not $lanAttempt.Wait(3000) -or -not $lanSocket.Connected) { throw 'No response' }
        Write-Host ('OK    {0}:{1}' -f $lanAddress, $lanPort)
    } catch {
        $lanFailures++
        Write-Host ('FALLO {0}:{1}' -f $lanAddress, $lanPort)
    } finally { $lanSocket.Dispose() }
}
if ($lanFailures) { Write-Host 'Revisar servidor y firewall de la red LAN.'; exit 1 }
Write-Host 'Los tres puertos responden desde este PC. Falta comprobar la entrada al juego.'
