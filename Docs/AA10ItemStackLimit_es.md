# Stacks de items hasta 99.999 en AA10 r575

## Resultado buscado

Las plantillas que en Returns 10.0.2.13 r575 admiten exactamente `1.000` o
`9.999` unidades por stack pasan a admitir `99.999`. El segundo grupo incluye
Tax Certificate (`31891`) y Bound Tax Certificate (`31892`). Los topes con otra
semántica (`1`, `10`, `100`, `255`, `999`, `5.000`, `int.MaxValue`, etc.) no se
alteran.

El cliente y AAEmu deben leer el mismo valor. Cambiar sólo el servidor permite
crear stacks que la UI no considera válidos; cambiar sólo el cliente hace que
el inventario del servidor siga fragmentándolos a `1.000`.

## Contrato confirmado

- Cliente: `game/db/compact.sqlite3`, tabla `items`, columna
  `max_stack_size INTEGER NOT NULL`.
- Servidor: `ItemManager` carga esa columna en `ItemTemplate.MaxCount` como
  `int32`.
- Wire: `Item.Count` se lee y escribe como `int32`.
- Persistencia: el conteo de items usa `INT`; `99.999` queda muy por debajo de
  `2.147.483.647`.
- Perfil cliente r575: 2.531 IDs exactos, SHA-256 de la lista ordenada
  `14C1BA767C5E3A077FCCDB177C146423DFFB493502B8B7B0CC63E7B68D6223BE`.
- Perfil runtime autoritativo: 2.771 IDs exactos, SHA-256
  `8146AEA01F997FBF357EB3299F8D7F693ECDFAD348B9A37F3A255ADA61D28C8D`.

El builder reconoce retail intacto, la primera versión que sólo elevaba el
grupo `1.000`, y el resultado final. Rechaza cualquier otro estado parcial.

## Artefactos versionados

- `Scripts/PatchAa10ItemStackLimit.py`: builder transaccional, dry-run por
  defecto, `quick_check`, identidad exacta, idempotencia y tamaño fijo.
- `Scripts/ApplyAa10ItemStackLimitGamePakPatch.ps1`: extracción efectiva,
  backups, construcción determinista, reemplazo verificado, rollback y
  `manifest.json`.
- `Scripts/tests/test_patch_aa10_item_stack_limit.py`: éxito, migración desde
  v1, idempotencia, dry-run y rechazo de identidades/estados parciales.

No se versionan SQLite, `game_pak`, reemplazos ni backups.

## Identidades de compact

| Destino | Tamaño | Antes | Después |
|---|---:|---|---|
| `game_pak:game/db/compact.sqlite3` | 440.823.808 | `84038AAF7EEE120A4218F8B1CE5FE14E1D9C949B8F92814BB4A040128D676BE8` | `7472265C95AB20E1E13D9BBD696258E25704C67D405DEF249784FBFA0AD50C74` |
| Cliente suelto `game/db/compact.sqlite3` | 440.832.000 | `FEFD3700177EFDE7B16176A229B92A4F2048C34E07DCB088E0E8F56F00625772` | `F12818D3B0E765C4F761C9587FD84E99DF7E7E64DC51C22647191F9A284B1F75` |
| Runtime `.server_files/AAEmu.Game/Data/compact.sqlite3` | 552.178.688 | `12C9A1254306E1677807EE57F77A37F2262814D624FE8E66DB7F438BEB9ECCA2` | `1BA34AE534DB13B7E7268D2F723BE69B39FB2EE83E3F6D747FE0AFC69F4E642D` |

El aplicador también admite instalar directamente desde las identidades retail
pre-v1; sus hashes finales deterministas están incluidos en el script.

## Aplicación

Dry-run reproducible:

```powershell
pwsh Scripts\ApplyAa10ItemStackLimitGamePakPatch.ps1 -SkipFullPakHash
```

Aplicación real:

1. Cerrar `archeage.exe`.
2. Detener únicamente el servicio Docker `game`; no operar Zones desde este
   parche.
3. Ejecutar:

   ```powershell
   pwsh Scripts\ApplyAa10ItemStackLimitGamePakPatch.ps1 -Apply
   ```

4. Iniciar Game, comprobar health/puertos y pedir al usuario que relance desde
   Control Center sólo la Zone necesaria.

El directorio impreso contiene las tres copias previas y `manifest.json`. Una
segunda ejecución debe detectar los hashes parcheados y no volver a escribir.

Aplicación v1 del 2026-08-30 (sólo grupo `1.000`):

- `game_pak` conservó 68.963.258.880 bytes;
- SHA-256 completo: `9DAEA9882FDB78A594D145BE95D087EEC4F2CEF08E47A43B633241A0011A4504`
  → `F2F60AD40EC4CA7EDB30AA204A12851F387A007422BBA892542FCA5C77E12050`;
- rollback y manifiesto:
  `E:\AAEmu\rama_10\backups\client-patches\aa10-item-stack-limit-20260830-202248Z`;
- la repetición `-Apply -SkipFullPakHash` reportó cero filas por cambiar en los
  tres targets y no reescribió el paquete;
- la reextracción de `main_world/en_us/world.dds` y
  `icon_item_0094.dds` pasó después del reemplazo.

## Aceptación retail v2

Con un material cuyo tope original sea `1.000` y con Tax Certificate, cuyo
tope original es `9.999`:

1. juntar más de 1.000 unidades en un mismo slot;
2. separar y volver a fusionar el stack;
3. reloguear y confirmar que el conteo persiste;
4. confirmar al menos un stack superior a `10.000` para Tax Certificate;
5. opcionalmente confirmar que `99.999` permanece en un slot y que la unidad
   100.000 abre un segundo stack;
6. comprobar un item no apilable y uno con límite retail `100` para demostrar
   que sus reglas no cambiaron.

La ampliación v2 no se considera aceptada dinámicamente hasta superar `10.000`
Tax Certificates en un único stack y confirmar su persistencia tras relog.

## Aceptación dinámica del 2026-08-30

Personaje `Dannia` (`characterId=1007`), Zone 142:

1. se entregaron dos lotes normales de 1.000 unidades de `Copper Ore`
   (`templateId=3411`) mediante `/item add`;
2. servidor y cliente mostraron un único stack de 2.000 en el slot 3;
3. el usuario volvió al selector de personajes y entró nuevamente;
4. tras el relog, la UI mantuvo correctamente las 2.000 unidades;
5. el snapshot Web API confirmó un solo item `16777359`, template `3411`,
   `Count=2000`;
6. MySQL confirmó exactamente una fila para owner `1007`/template `3411`:
   item `16777359`, `count=2000`, `slot_type=2`, `slot=3`.

Resultado v1: **aceptado dinámicamente** para fusión superior a 1.000,
serialización cliente, persistencia y relog. El borde exacto 99.999/100.000
permanece cubierto por el contrato `int32`, los límites sincronizados y las
pruebas estáticas; no fue necesario inyectar 100.000 items al inventario del
personaje de prueba. La aceptación v2 para Tax Certificate queda pendiente de
la aplicación y la prueba descrita arriba.
