# AA10 Archery: Neblina — 2026-09-11

Actualización V2: el usuario confirmó flechas visibles y reportó elevación y
seguimiento aparente en dos videos. Ver `Docs/AA10NeblinaDirection_es.md` y
`skills/archery_mist/delivery-direction-manifest.json`. Se retiró la suma
injustificada de8 m de RandomArea.p4; 2767 tests verdes. El targeting original
exacto, la sexta flecha y el daño cercano siguen abiertos.

Estado: **correcciones parciales desplegadas; aceptación retail pendiente**.
No marcar skill36473 como reconstrucción completa.

Dossier y guía reutilizable: `Docs/AA10NeblinaReconstruction_es.md`.
Código reproducible y manifest: `reconstruccion_cliente_10/skills/archery_mist`.
Evidencia: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archery-mist-repair-20260911`.

Se corrigieron SCPlotEvent/lista de unidades, multiplicidad de efectos por
selector, Range0..8 independiente del cono30 m y tickets por historial de rama.
Sin cambios de balance, cliente, compact ni DB. Sin lifecycle de Zones.

Restore/build Release correctos; 2765/2765 tests. Fixture nativo embebido de
plot2957. La prueba del recorrido de relleno emite5 proyectiles a posiciones;
el test separado de tickets confirma disponibilidad10×6, **no60 flechas renderizadas**.
Conocimiento SQLite determinista, integridad ok, cero aristas huérfanas.
16 funciones release reancladas contra el PE principal español; el compact
extraído del paquete tiene cero diferencias operativas en la clausura auditada.

El despliegue recreó sólo `aaemu10-game-1`. Imagen anterior conservada como
`aaemu-world:before-neblina-20260911`. Los hashes exactos, imagen nueva, gates
de arranque y respaldos están en `delivery-manifest.json` y la evidencia.

Siguiente paso: resultado del usuario con arco y sin objetivos. Después,
medir salvas/posición de impactos y capturar la frontera de variables nativas
que filtra la sexta flecha. Permanecen abiertos RandomArea.p4 y la fórmula de
daño cercano−20%. No sustituir esos contratos por la hipótesis de AA8.

La lista cero de SCPlotEvent era incorrecta, pero **no suprime por sí sola los
efectos Location**: el consumidor release los ejecuta una vez independientemente
de la lista de unidades. Mantener esta corrección sobre la hipótesis inicial.
