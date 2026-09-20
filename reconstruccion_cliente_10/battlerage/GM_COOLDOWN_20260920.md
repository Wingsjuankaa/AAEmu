# Comandos GM de cooldown AA10 — 20/09/2026

Target `rama_10`, base `33c0d8379`. Padre inspeccionado:
`upstream/client_version/zone-10.0.2_r575` en `7851f67cc`.

## Uso

- `/ignorecd true`: limpia ahora los cooldowns de habilidades de jugador y
  sus grupos, y los vuelve a limpiar al finalizar/cancelar cada habilidad.
- `/ignorecd false`: restaura el comportamiento normal para los usos siguientes.
- `/resetcd`: limpieza puntual, sin activar el modo continuo.
- Alias conservados: `ignoreskillcds`, `disablecooldowns`, `ignorecooldowns`;
  para reset puntual: `resetskillcooldowns`, `rcd`.

El modo es de la sesión del personaje; no se persiste tras relog. Conserva GCD,
animaciones, canales y enlaces/ventanas de Combo. No convierte un botón en spam
sin animación. Tampoco repone cargas ni elimina cooldowns de cuenta: son recursos
separados y esta corrección no certifica esas familias.

## Causa comprobada

`IgnoreCooldowns` sólo asignaba el booleano y no limpiaba los cooldowns existentes.
`ResetSkillCooldown`/`ResetAllSkillCooldowns` eliminaban el ID individual pero no
los grupos introducidos en `2ad4c229f`. El cliente también conservaba esos grupos
porque `rstc` se enviaba desactivado. Frenesí 10455 tiene 90 s y grupo 4603;
Hendir la tierra/ancestral 10644/41217 comparten 4156. Por eso un reset individual
no desbloqueaba la habilidad, aunque el método se hubiese ejecutado.

El padre mantiene el comando con el mismo comportamiento. La sesión previa de
Dannia ya registró `/resetcd` seguido de cooldown aún visible en Frenesí. No se
necesitó modificar SQLite ni el cliente para reproducir el defecto.

## Corrección acotada

Se permite pedir expresamente `resetSkillTags` en el método de reset. El modo GM
lo solicita desde EndSkill, Stop y DoPlotEnd; la limpieza global lo solicita para
los miembros de tag378, que incluye las variantes ancestrales inspeccionadas.
Se eliminan los mismos grupos en World y se emite el flag nativo `rstc` al cliente.
Activar el modo limpia inmediatamente y confirma su estado por mensaje.

Los resets de respuestas fallidas de `CSStartSkillPacket` mantienen el valor
predeterminado anterior: no se amplía su alcance ni se altera su GCD. No se
modifican `ArmCooldowns`, los gates de lanzamiento ni las transiciones aceptadas
por el usuario en `f8af778cf`.

Contrato de paquete y consumidor: [NATIVE_RESET_COOLDOWN.md](NATIVE_RESET_COOLDOWN.md),
SHA/x64/RVA y semántica `rstc` ya cerrados allí. Las pruebas comparan el paquete
emitido realmente por Character mediante una conexión de prueba.

## Validación

Dos regresiones nuevas fallaron antes de la corrección: grupo 4603 aún activo
tras reset puntual y tras activar modo continuo (8 correctas, 2 fallos).
Se añadieron otros dos casos para comprobar los tres grupos, el flag enviado,
GCD conservado y semántica anterior de las respuestas de error. La prueba de
comando también cubre desactivación y entrada inválida sin borrar cooldowns.

Restore y build Release correctos. Suite completa: **5.515 correctas, cero fallos**.

La validación jugable corresponde al usuario, conforme a su instrucción de
retomar el cliente. No se abrió ni controló el cliente ni se operaron Zones.
Siguiente prueba: usar Frenesí, ejecutar `/ignorecd true`, esperar sólo el GCD y
volver a lanzarlo; después `/ignorecd false` y confirmar que un nuevo uso mantiene
su cooldown. Evitar dejar el modo activo al valorar el balance normal de skills.

Reportes abiertos 9/8/7/5 inspeccionados: ninguno describe este comando; no se
cambiaron sus estados. Evidencias: `E:/AAEmu/rama_10/artifacts/gm-cooldown-20260920`.

## Despliegue

Game reconstruido y recreado; Login/DB conservados. Imagen:
`b5abd428e4b3b07f6323848cc09050fed6088b332e43e489dad12ffe2a5f89f2`.
DLL Linux verificada en `/app` y `/app/game`:
`732c2284efb21d4947c087bc2384830b0c22cf865880d3757b8880769ba8322c`.
Compact efectiva sin cambios:
`85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
Rollback: `aaemu-world:rollback-pre-gm-cooldown-20260920`, imagen anterior
`b8085e5ae54f0b9138c5f3d9822a5123f00f80e8176d82aad534b267b5350b25`.
El reinicio de Game fue anunciado al usuario; el relanzamiento de sus Zones
continúa bajo su control.

Arranque confirmado a las 17:34:27 UTC: GameService Server started, GameNetwork
y StreamNetwork escuchando; evidencia startup.log. El arranque conserva errores
de definiciones de smelting 29–32, ajenos a esta corrección.
