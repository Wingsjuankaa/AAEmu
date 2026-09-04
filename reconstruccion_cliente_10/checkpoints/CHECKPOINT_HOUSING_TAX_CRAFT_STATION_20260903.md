# Housing / crafting — placas de impuestos AA10 (2026-09-03)

Target `rama_10`, HEAD base `41570558459efad934065d3ea348bffc52f45162`;
padre exacto `upstream/client_version/zone-10.0.2_r575`, `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.

## Reproducción y causa

Dannia reprodujo el error en retail. Log Game 22:48:04:

```text
CSExecuteCraft, craftId : 76 , objId : 101010, count : 1
Rejected AA10 craft before skill start: character=1007, craft=76,
skill=16767, failure=StationUnavailable, blocker=None, result=NoPerm
```

La creación del objeto 101010 registra template9405 y fase26178. El rechazo no fue
`PermissionDenied`: el validador exigía igualdad literal con `req_doodad_id=2392`.
Ambos fallos se presentan como NoPerm. No hubo casteo ni commit en ese intento.
La captura corresponde a **Bound Tax Certificate (receta76)**, no a Tax Certificate9267.

Full r575 y compact retail actual coinciden en esta cadena:

```text
craft76 -> req_doodad2392, skill16767
doodad9405 -> phase26178 -> func22855 (DoodadFuncCraftPack, perm0/Public)
 -> actual_func408 -> craft_pack3 -> craft_pack_crafts11050 -> craft76
```

Identidad full: `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
Identidad compact: `F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B`.
La captura más esos datos prueban que esta variante ofrece la receta. No se toma
la limitación de igualdad literal de AA8 como contrato AA10. Upstream padre
conserva comprobaciones antiguas de permisos, no una solución transferible segura.

## Arreglo

- Reconocer una estación alternativa sólo mediante su CraftPack activo y la
  pertenencia cargada de la receta; no añadir excepción por ID ni cambiar SQLite.
- Evaluar permiso de la función de crafting coincidente, no el primer callback
  de la placa (que también puede contener administración/Butler).
- Conservar fail-closed para permisos de función no públicos no reconstruidos.
- Revalidar acceso Housing antes del cast, por unidad del lote y antes del commit.
  La excepción pública de taxes se aborda en el siguiente arreglo cross-account.
- Mantener la ruta canónica de estaciones y las transacciones existentes.
- Registrar template, estación requerida, fase y casa en futuros rechazos.

## Validación

Restore y build completo Release: correctos, cero errores. Advertencias preexistentes
de código/dependencias (incluyendo advisories NuGet) no corregidas por este cambio.
Suite completa: **1762/1762**, cero fallos/omitidas. Seis regresiones nuevas cubren
placa9405, catálogo incorrecto/ausente, estación inexistente, permisos de función,
revocación de acceso Housing y salida de fase. `git diff --check` correcto.

No se modifica cliente, configuración, esquema SQL, inventarios ni balance.
H2 cross-account y H5-B no quedan globalmente aceptados por este arreglo.

## Despliegue y aceptación

Imagen construida: `sha256:92a41248a630a6d2d986ca1f6ddd27e18b140a0e6de797f46acd1e57fa63474d`.
Rollback: `aaemu-world:rollback-pre-housing-tax-station-20260903`, imagen
`sha256:fd6330cdbd072e1a9fbde4091e2f1a7c0407306688641fab01aca8712c20adf5`.
Game detenido limpiamente22:57:43 (exit0): `SaveManager` guardó un personaje,
sin excepción de guardado. Backup posterior al stop:
`E:\AAEmu\rama_10\backups\housing-tax-station-20260903\aaemu_game.sql`, 205129 bytes,
SHA256 `2E807E523EF16D6D84B8C37DDE7334CA3C6D9ABE58D8328635870C05A68FFBA8`.
Se recreó sólo Game con `--no-deps --no-build`; Login/DB no se reinician.
SHA256 DLL idéntico en `/app` y `/app/game`:
`189a4c8edaf63851a6357c8fedc4390802f49df2d91e6414ce2f5d58c89c15a2`.
Imagen vigente coincide con la candidata. Housing reconciliado22:59:27;
`Server started!`22:59:28 (74,75s), GameServer1 registrado en Login.
Game healthy, cero reinicios. Login/DB conservan sus mismos IDs y estado healthy.
Los errores de Smelting29–32 son anteriores y su feature sigue OFF; no se reabre
esa mecánica. La desconexión Zone durante el reinicio es esperada y no se operó su lifecycle.
Zone queda bajo control del usuario.

## Aceptación retail — 2026-09-03

El usuario confirma «perfecto ya funciona». Game registra dos ejecuciones de
Dannia (character1007), craft76, estación101010, cantidad1:

- Solicitud23:07:45, commit23:07:51.
- Solicitud23:07:55, commit23:08:00.
- Ambas: `materials=1, products=1, failedProducts=0, cost=1, labor=55, remaining=0`.

El fallo de reconocimiento de placa queda **ACEPTADO Y CERRADO**: repetición
positiva y resultado visible confirmados. Los contadores materials/products del log
representan entradas del plan, no cantidades unitarias de objetos.
Esto no acredita lotes, persistencia tras otro reinicio ni la matriz cross-account:
esos gates de Housing permanecen abiertos. No hubo nuevo despliegue en este cierre.
