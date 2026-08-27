# Items de montura y battle pet AA10

El servidor usa un catálogo cerrado de 478 contratos AA10 r575. Cada contrato
une exactamente un template de item, su skill de uso y el NPC que debe crear.
Una relación no incluida se rechaza; nunca cae al flujo legacy.

En Docker, `Data` está montado desde `.server_files`; antes de desplegar hay que
copiar allí `AAEmu.Game/Data/aa10-summon-mate-policy-v1.json`.

Para una validación funcional, entrega el item mediante el canal GM interno y
mantén el item en la bolsa. Comprueba invocar, retirar con una segunda pulsación,
montar/desmontar y reloguear después de variar HP/MP o EXP. El item no debe
consumirse. Si el mate tiene equipo, el servidor debe impedir destruir el item
de invocación; después de retirar el equipo, destruirlo debe retirar también el
registro persistente del mate.

El gate retail r575 del 2026-08-27 aprobó invocación, retirada, reinvocación,
mount, guardado, relog sin duplicación y rechazo fail-closed. Para regresiones
locales existe la cuenta `codexmate0827`, personaje `Mateprobe`, con un fixture
executable (template 4177) y otro bloqueado (template 39711). Su contraseña no
se almacena en el repositorio: la credencial DPAPI está en
`C:\Users\juank\AppData\Local\AAEmu\test-accounts\aa10-r575-retail.clixml` y
sólo puede descifrarse bajo el usuario Windows que la creó.

El inventario completo de contratos y bloqueos, hashes, gates y procedimiento
de aceptación está en
`reconstruccion_cliente_10/CHECKPOINT_NATIVE_SUMMON_MATE_V1.md`.
