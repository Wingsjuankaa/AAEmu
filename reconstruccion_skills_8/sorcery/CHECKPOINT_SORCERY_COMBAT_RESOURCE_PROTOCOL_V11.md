# Checkpoint Sorcery combat-resource protocol V11

Fecha: 2026-08-05

## Resultado

La repetición del banner de especialización durante Insulating Lens no era un
loop del buff ni un efecto específico de `skill 10153`. Era una colisión de
opcode en el protocolo G2C AA8:

- `SCCombatResourcePointPacket` estaba registrado como `0x175`;
- `0x175` pertenece a `SCAbilitySwappedPacket`;
- el cliente interpretaba cada actualización del recurso Magic Source como un
  cambio de especialización y reproducía el banner de clase.

La corrección asigna al paquete de puntos su opcode AA8 nativo `0x315`. No se
modificó la SQLite V10, la duración del buff, la regeneración, el cooldown ni
la semántica del escudo.

## Evidencia en vivo previa

El cast de `10153 Insulating Lens`, timeline `2052`, a las `22:58:39` completó
su lifecycle normalmente:

- `use_result=Success`;
- `fired` tras 1.500 ms;
- dos efectos seleccionados y aplicados;
- `buff 95` creado;
- Magic Source pasó de 0 a 20;
- `ended` limpio y no cancelado;
- al terminar los 40 segundos se aplicó el cooldown diferido de 30 segundos.

Entre la aplicación y el agotamiento del recurso, Game emitió 21 veces:

```text
type 175 .G2C.SCCombatResourcePointPacket
```

Son el punto inicial 20 más el descenso por segundo hasta 0. El usuario observó
un banner Stormcaster por cada paquete. También confirmó que el patrón aparece
con las demás skills que otorgan un buff/recurso al propio personaje, lo que
establece el alcance transversal.

Captura estructurada de la sesión:

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-insulating-lens-resource-opcode-before-fix.json
SHA-256: 5262605A066AA379E5543E621B1028281E8924C64B15B271E3EFFB66CB903096

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-insulating-lens-resource-opcode-before-fix.csv
SHA-256: C5B7D4DE6F8F8CBECC90457DE48651F4EE64DFEA869333A3FE6261E3B904B3D9
```

## Prueba nativa AA8

Autoridad binaria:

```text
module: x2game.dll x86
SHA-256: 078DB1B94236ECB8BBE21DC5C71CE90C178D51B6BF261C4767D32A44809BDDC3
image base: 0x39000000
corpus: E:\AAEmu-Research\output\aa8-native-code\stage-15-native-code.sqlite
```

La fábrica `FUN_3933ffe0`, RVA `0x0033FFE0`, asigna una instancia de `0x28`
bytes, instala `PTR_LAB_3A093E3C` y escribe explícitamente `0x315` en el campo
de opcode. Las referencias de datos confirmadas a esa vtable provienen de
`FUN_392F2720` y de la propia fábrica.

El serializer `FUN_39B6C080`, RVA `0x00B6C080`, demuestra el layout:

1. `bc objId`, tres bytes, offset `0x0C`;
2. resource id de 32 bits, offset `0x10`;
3. `point` de 64 bits, offset `0x18`;
4. `updateTime` de 32 bits, offset `0x20`.

Las dos familias contiguas confirman que no se desplazó la tabla:

| Paquete | Fábrica | Serializer | Opcode | Cola |
|---|---:|---:|---:|---|
| resource point | `0x0033FFE0` | `0x00B6C080` | `0x315` | `point`, `updateTime` |
| resource transform | `0x00340070` | `0x00B6C110` | `0x370` | `prevDefaultResourceActive` |
| resource update time | `0x00340100` | `0x00B6C190` | `0x36E` | `isMove` |

`SCAbilitySwappedPacket` conserva `0x175`; los dos contratos ya no comparten
TypeId.

## Implementación

- `AAEmu.Game/Core/Packets/G2C/SCOffsets.cs`:
  `SCCombatResourcePointPacket = 0x315`.
- `AAEmu.Tests/CombatResourceRuntimeTests.cs`:
  prueba explícita del TypeId, no colisión con `SCAbilitySwappedPacket` y
  conservación byte a byte de los tres layouts.

## Validación automatizada

- 11/11 pruebas dirigidas de recurso y serialización de estado.
- 496/496 pruebas C# completas en Docker SDK .NET Core 3.1.
- Los warnings NU1701 preexistentes no alteraron el resultado.

## Despliegue

- Imagen Game: `sha256:94673304defc3f36109137e0aa4bce65b409a2bf673592cff96d01d499139f07`.
- Rollback: `aaemu-game:rollback-pre-combat-resource-opcode-fix-20260805`.
- Sólo se recreó el servicio `game`.
- Runtime montado: `compact-8.0-runtime-transversal-sorcery-v10.sqlite3`.
- SHA-256 verificado dentro del contenedor:
  `FB77DC60360C1BF5B9D683C945CD11FCA4736034B75EB16D1C5C4FBBFF065876`.
- GameNetwork `2239`, StreamNetwork `2250` y registro en Login confirmados.
- Arranque completo en `00:01:40.4193321`, sin errores de compilación.

## Gate en vivo pendiente

Después del despliegue, un único cast de Insulating Lens debe mostrar:

- `type 315 .G2C.SCCombatResourcePointPacket` durante el descenso de Magic
  Source;
- cero `type 175 .G2C.SCCombatResourcePointPacket`;
- escudo y recurso activos sin repetir el banner Stormcaster;
- fin del buff a los 40 segundos y cooldown diferido de 30 segundos.

La rotura anticipada del escudo y su explosión de hielo se validarán como gate
separado; este checkpoint sólo cierra la colisión transversal de protocolo.
