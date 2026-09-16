# Nuia: misiones amarillas — diagnóstico 2026-09-15

## Estado de entrega

Auditoría reproducible terminada. No se reprodujo el síntoma de interacción en
cliente; no se aplicó ni desplegó una reparación de gameplay. La aceptación de
las misiones del caballo y del bote queda pendiente. Este checkpoint no altera
el despliegue racial de `CHECKPOINT_NUIA_ALPHA_20260915.md`.

Informe: `Docs/AA10NuiaYellowQuestAudit_es.md`.
Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nuia-sidequests-20260915`.
Manifest: `NUIA_SIDEQUESTS_20260915.manifest.json`.

## Hallazgos

- 2.567 misiones normales catalogadas: 1.184 regionales y 1.383 de zona genérica1.
- 11.070 actos habilitados/72 tipos; detalles y cargadores presentes, sin probar
  ejecución completa. 689 objetos referenciados; 74 con fuente de item plantable.
- 18.898 filas mecánicas comparadas: sin diferencias full/compact de servidor.
- 313 diferencias de crecimiento en compact cliente coinciden con el rate100
  montado, antes de clima. No son una reparación pendiente de tiempos.
- 7.405 posiciones main_world; 4.571 diferencias de presencia entre catálogos
  para 353 plantillas. Incluye redondeos y posiciones no Nuia de objetos
  compartidos; no habilitar como carga masiva.
- Seis tipos de función sin clase/cargador local; falta cerrar consumidor
  cliente/Game/Zone. `DoodadFuncSpawn` enlaza objetos1365/2936/11651 y misiones
  regionales1402/1474/2071. Upstream tampoco tiene esa clase. AA8 sí, como
  `structural_candidate`, no autoridad para el spawn de NPC en AA10.
- Bote2393: actor2853, fase6378, FakeUse14006, LootItem17863. Cinco instancias
  nativas/fuente, cuatro en runtime con inclinación45 en vez de53. La diferencia
  existe; no demuestra la causa del clic sin respuesta.
- Caballo4292→4294→4295: semilla23635→4594; cosecha21850; potros23680/81/82
  →4725/4727/4743→monturas8159/60/61. Las cuatro plantillas dinámicas no tienen
  posiciones nativas fijas; no se deben añadir para eludir plantación/crianza.
- Los nombres del piloto provienen del compact español instalado. No se
  modificaron traducciones ni se atribuyeron diferencias de gameplay a es_ES.

## Cambios de herramientas

`audit_nuia_sidequests.py`: scope normal occidental, acciones y títulos españoles.
`classify_nuia_sidequests.py`: contratos de objetos fijos y dinámicos, contraste
de cuatro bases read-only, consumidores y matriz de prioridad.
`audit_hiram_onward_quests.py`: expansión opt-in a `item_spawn_doodads` y modo
diagnóstico opt-in que registra divergencias en vez de abortar. Conserva el modo
estricto por defecto y el generador rechaza contratos divergentes.

## Gates

Restore correcto; Release 0 errores/28 advertencias; 2.836 unitarias correctas,
0 fallidas/omitidas. `py_compile` correcto para las tres herramientas y diff
check sin errores de whitespace. Los tests validan el árbol local actual, no
constituyen aceptación retail del piloto.

Consulta de reportes pendientes de categoría quest: reporte3/10029 de Garden,
sin un reporte identificable del síntoma actual. El usuario no recuerda los
nombres: el piloto corresponde a las cadenas iniciales candidatas de Solzreed.

## Continuación concreta

Usar `acceptance-pilot.csv` (11 pasos pendientes). Primera evidencia necesaria:
interacción de bote2853 con misión2393 activa, registrando si aparece request
skill14006, fase actual, respuesta y modificación de inventario. Para caballo,
capturar creación de4594 desde23635 antes de investigar cosecha/potros. No asumir
que un `SummonDoodad` con ID nulo es el camino real de colocación.

Tras reproducir, corregir y propagar por mecanismo; después ampliar a objetos
fijos regionales con geografía confirmada y a funciones de objetivos faltantes.
Mantener la racial nuiana como regresión. No operar Zones ni rellenar miles de
posiciones para compensar un problema de protocolo o fase.
