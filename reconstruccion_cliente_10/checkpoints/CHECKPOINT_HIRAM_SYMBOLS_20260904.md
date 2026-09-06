# Quest 9190: símbolos de Hiram y caída de Zone350

## Alcance y autoridad

- Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`.
- Padre exacto `upstream/client_version/zone-10.0.2_r575`, SHA `3cc280b14d7da0d874121d14ebbf409f5e032d1c`; conserva el mismo emisor de retirada de buffs sin filtro de unidad.
- Clasificación: `server-required`, catálogo AA10 y consumidor dedicate r575. Sin cambios en cliente, SQLite, DLL nativa ni lifecycle de Zones.
- Evidencia reproducible: `scripts/audit_hiram_symbols_9190.py` y `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/hiram-symbols-9190/`.

## Cierre de Zone350

A las 14:54:25 UTC Game rechaza enviar la creación del buff 23137 porque su propietario es el doodad 101263 (template 13443). El catálogo fija su duración en 5000 ms. La retirada carecía de ese filtro y se enviaba a la Zone primaria mediante `ForUnit`.

La caída de las 14:54:31 UTC está conservada en el minidump y `zone-350.crash`. El binario cargado es `x2game-dev_dedicate.dll`, base `0x39000000`, SHA256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`:

- RVA `0x364DE0`: recibe el objetivo y el índice del buff.
- RVA `0x35C830`: lee directamente `unitTable[id]`, sin comprobación de rango.
- RVA `0x450420`: `ZoneBuffMan::Destroy`.
- RVA `0x450A7A`: acceso inválido a `rcx+0xCA8`; `rcx=0x00656c61635386D0`.

El dump pequeño no incluye el paquete en heap; la identidad del objetivo se correlaciona con el warning de creación, su duración y el índice 2 en el contexto de caída. No atribuir el fallo a un teletransporte. El retorno a selección de personajes es la reacción posterior de World al perder Zone350.

Se restringen retirada y actualización de buffs al rango nativo de unidades (1..100999), como ya se hacía para su creación. Los buffs locales de doodads conservan su lifecycle y sus notificaciones al cliente.

## Cadena nativa de la daga

La clausura coincide entre `game_decrypted.sqlite3` y compact montado:

1. Quest9190 exige efectos 73148/73151/73152 y recoger item46558.
2. Skills40092/40093/40094 aplican una acumulación de buff23652 al actor (`SourceOnce`).
3. Buff23652: `Multiple`, `max_stack=3`, `transform_buff_id=23653`; su descripción nativa confirma transformación al reunir tres símbolos.
4. Buff23653: duración1000 ms, trigger11061 `Timeout` -> efecto73153 -> SpecialEffect38819, `GainItem(46558,0)` (cantidad predeterminada1).

`TransformBuffId` se cargaba pero no se usaba. Ahora los buffs Multiple con transformación configurada consumen sus instancias activas al alcanzar el máximo y crean el buff de destino conservando fuente y nivel. Se valida el destino antes de consumir. No se transforma estado escrito por la Zone ni se modifica el comportamiento de buffs sin transformación. La daga la entrega el trigger existente; no se agrega una recompensa artificial a la quest.

## Verificación y recuperación

- Build Release y suite completa: 1799/1799; tres pruebas nuevas cubren rango de unidad, tres acumulaciones, timeout único, tareas pendientes, destino ausente y buff ordinario.
- El estado observado de Dannia tenía objetivos `[1,1,1,0]`, sin daga ni items46611. La persistencia anterior dejó buff23652 con una sola acumulación. No se reescribió el personaje ni se inventaron stacks faltantes.
- Para el estado previo: abandonar y volver a aceptar9190. La aceptación nativa ejecuta skill40144 (DispelEffect3635/tag3949/stack3) y vuelve a suministrar tres items46611. Repetir los tres símbolos; el tercero debe entregar la daga tras el timeout nativo de un segundo.
- La persistencia general de buffs Multiple conserva limitaciones previas (una fila por buff y restauración de una instancia); esta entrega no la rediseña. Probar la secuencia sin desconectarse entre símbolos.
- Aceptación retail confirmada por captura del usuario y logs16:18:34 UTC: Dannia completó9190, entregó la daga y aceptó9191. No hubo reproducción adicional del crash bajo depurador.

## Despliegue y rollback

- Imagen candidata/operativa: `sha256:d016f25793a5c76ccf4c5d67478d7549cd582981cb0b594b250a02fd9bd0f697`.
- Rollback: `aaemu-world:rollback-pre-hiram-symbols-20260904` = imagen `6a5f50cef8396f8bd12c24c0525dee886b6f49a805c68f1015f2dd650a3644ad`.
- DB: `E:/AAEmu/rama_10/backups/hiram-symbols-20260904/aaemu_game.sql`, SHA256 `49d43e88aa30b3c8d5fb273c70a47555ff6cd5e31bb57be3602caff9c2eadbc1`.
- Sólo se recreó Game con ambos compose canónicos; conservar DB/Login, puertos y mounts.
- Verificado: DLL en `/app` y `/app/game` SHA256 `a9750c48370305d2b0dde959cd358bf80ea6e5801d7b3dfbebf014cdb2478467`; registro en Login, API interna y45785 doodads. DB/Login conservan sus contenedores saludables. API a las15:21 UTC: Zones vacías; el usuario debe levantar350 desde Control Center para aceptación.

## Aceptación de arreglo anterior

Los logs muestran que Dannia completó9180 y avanzó por9182..9190. Esto confirma el avance retail tras el arreglo de entrega a Andega documentado en `CHECKPOINT_NEMI_RIVER_REPORT_20260904.md`.
