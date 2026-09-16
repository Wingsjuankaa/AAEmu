# Parches locales sobre el snapshot

## 0001: destino RIP del administrador de barcos

Base: NickMesser/AAEmuZoneHost `8801e8272309b53288b63c4869a83f01b42eae14`.
Target: x64 r575 `x2game-dev_dedicate.dll`, SHA-256
`8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`.

La instrucción sobrescrita en RVA `0x360862` es
`48 8B 15 4F 87 2D 01` (`mov rdx,[rip+0x012D874F]`). Su siguiente RIP es
`0x360869`; por tanto el global está en RVA `0x1638FB8`. El stub upstream
transcribía `0x1738FB8`, un megabyte por encima. Al regresar a la instrucción
`mov rax,[rdx+8]`, dos invocaciones de Moby Drake causaron acceso a dirección 8.
Ambos minidumps de Zone 179 del 2026-09-16 muestran `RDX=0`, RIP `0x39360869`.

El parche deriva la dirección de los bytes nativos y conserva el resto del hook
de física. Las pruebas decodifican el desplazamiento del stub emitido y verifican
su destino, salto de retorno y capacidad de la cueva. La auditoría PE confirma
el desplazamiento original antes de publicar. No deshabilita física ni oculta
la excepción con un retorno nulo.

Evidencia y dumps locales: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/fishing-summon-20260916/zone-crash`.
Decompilación relacionada: `zone-crash-decompile.log` en el directorio padre.
La aceptación de gameplay requiere volver a invocar en la Zone; build y pruebas
no inician procesos de Zone.
