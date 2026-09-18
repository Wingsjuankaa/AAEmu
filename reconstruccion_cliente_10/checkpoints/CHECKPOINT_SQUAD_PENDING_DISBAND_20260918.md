# Squad: disolución pendiente al reconectar — 2026-09-18

Target `rama_10`, branch `rama_10`, base `708f313f5281053d73cac3907ba0df8b5618f566`.
Padre consultado mediante fetch: `upstream/client_version/zone-10.0.2_r575`.
No se integraron otros cambios del padre. PR: https://github.com/AAEmu/AAEmu/pull/1633.

## Problema y corrección

La corrección anterior del aviso falso al login eliminaba `SCDisbandSquad` cuando
no existía equipo. Pero `DisbandLocked` sólo notificaba a personajes disponibles:
un miembro ausente perdía la disolución real. El revisor señaló que el cliente
puede conservar el equipo y el botón Reclutar deshabilitado.

Se conserva el login ordinario sin aviso de disolución. Cuando ocurre una
disolución real, se guardan los IDs persistentes de miembros ausentes, marcados
offline o sin conexión. Su próximo login recibe una sola vez `SCDisbandSquad`
antes de `ClearQueue`. Los miembros disponibles reciben el aviso inmediatamente.

El registro y consumo usan el mismo lock que las membresías. Un equipo nuevo
prevalece sobre el evento antiguo; recibir una disolución online también elimina
cualquier marcador anterior. No hay ventana entre la comprobación de membresía
y el envío que permita borrar por accidente un equipo creado concurrentemente.

Los marcadores viven en memoria, como los equipos actuales: no se afirma
persistencia después de reiniciar Game/World ni cobertura de pérdida de red tras
aceptar el envío. No se modifica la DB ni se cambia el cliente para ocultar avisos.

## Evidencia y pruebas

- Diagnóstico previo: `CHECKPOINT_TAX_TRADE_PROTECTION_20260916.md`; envío de
  SCDisbandSquad0x30D al ingresar sin equipo. El bit de feature107 allí descrito
  pertenece a otro problema y no se toca en esta corrección.
- BugReports, filtro UI y límite 50: ningún reporte activo devuelto.
- Reproducción antes del cambio en la rama PR: cinco casos nuevos, cuatro fallos
  y un éxito; demuestran eventos perdidos o enviados durante presencia offline.
- Versión final: seis casos nuevos más los dos existentes de login/disolución.
- PR Release: 4.606 pruebas aprobadas, cero fallos/omitidas.
- Rama local Release: 5.471 pruebas aprobadas, cero fallos/omitidas. Se incorporó
  también la prueba ya existente en el PR para el miembro online/equipo vigente.
- Se registran paquetes reales emitidos por `SquadManager.Disband` y
  `SyncClientSquadAfterLogin`, incluido orden de opcodes y ClearQueue.
- Se cubren reconexión con otra instancia Character del mismo ID, aislamiento
  de otros personajes, consumo único, nueva membresía y otra disolución posterior.

Esta validación es automática del servidor/transporte. No es una observación
nueva dentro del juego ni prueba de que el cliente borre solo su equipo al salir.
Se adopta la alternativa de avisos pendientes solicitada por el revisor.

## Entrega

Artefactos: `E:\AAEmu\rama_10\artifacts\pr1633-correction-20260918`.
Rama PR actualizada: `contrib/r575-squad-login`, commit `7ddee7b16`.
La descripción del PR recoge comportamiento, pruebas y límite de persistencia.
Imagen local Release: `aaemu-world:squad-login-fix-20260918`.
Rollback: `aaemu-world:rollback-squad-login-20260918`.
Hashes y verificación de arranque: `SQUAD_PENDING_DISBAND_20260918.manifest.json`.
No se operó el lifecycle de Zones. Login, DB, configuraciones y cliente se conservan.
