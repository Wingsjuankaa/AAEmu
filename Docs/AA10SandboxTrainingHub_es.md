# Laboratorio de entrenamiento AA10

El escenario posterior, con identidad Zone411 y terreno separado, se documenta
en [AA10SandboxSeparateZone_es.md](AA10SandboxSeparateZone_es.md). Este documento
conserva la implementación y la aceptación previas de los servicios en Hall379.

Fecha: 2026-10-29, America/Santiago. Target `E:/AAEmu/rama_10/server/AAEmu`,
`rama_10` HEAD `9c74824659cc0d144f5e450e3bd7157624e539c3`.
Padre obligatorio `upstream/client_version/zone-10.0.2_r575`,
SHA `78533663d9ca93dc4aa610c088359312f91f4293`.

## Espacio elegido

Se revisaron 70 world.xml del paquete español y 23 candidatos de zonas.
Existen arenas retail (`instance_training_camp`, Zone198;
`instance_training_camp_1on1`, Zone302; `no_item`, Zone322), pero en los
candidatos estudiados no quedó demostrado un hub con todos los servicios.
Algunos puntos legacy del servidor son placeholders y no acreditan entrada.

Se conserva la sala `main_world/gatekeeper_hall`, World0/Instance0/Zone379,
con entrada y movimiento previamente aceptados por el usuario. La escena se
personaliza con actores del catálogo retail. No se ha creado una nueva malla,
heightmap ni formato binario de mapa. Se conserva el decorado del nivel.
El inventario espacial sólo acredita pertenencia de zona; el suelo de cada
nueva posición debe comprobarse visualmente en el cliente.

## Contenido del perfil

Origen X500.295, Y38373.5, Z129.948, yaw0. Los cuatro dummies 7512 permanecen
delante. Los puestos se colocan detrás, a Forward=-3 y Right=-6/-2/+2/+6,
con la misma altura inicial. Se mantienen cerca del punto ya jugable.

| Puesto | NPC retail | Servicio real | Posición local F/R |
|---|---|---|---|
| Especializaciones | 18870 Toosten | ChangeSkillsets 12082 | -3 / -6 |
| Banco | 1023 Tiri | UseWarehouse 13238 | -3 / -2 |
| Armas | 1497 Vigdia | UseStore 12087, pack119 | -3 / +2 |
| Armaduras | 1498 Giyolla | UseStore 12087, pack219 | -3 / +6 |

Los nombres, títulos, modelos y vestuario proceden del cliente español
empaquetado (canal interno en_us). Las tiendas contienen 38 y 36 filas
estáticas respectivamente; sus costes e inventario siguen los consumidores
normales. No constituyen un catálogo completo de objetos de prueba.

Se descartó 14168 Administrador de la arena: sus once actos de reporte de
misión hacen que el diálogo prioritario oculte el cambio de especialización.
El manager valida la acción que el QuestManager realmente cargado ofrecerá,
además de las capacidades, no agresión y plantilla de cada NPC.

## Aplicación y repetición

Preset versionado: `Scripts/aa10_sandbox_training_hub.json`. Aplicador:
`Scripts/aa10_sandbox_hub.py`. Acceso del runtime:
`E:/AAEmu/rama_10/runtime/sandbox-aa10/Aplicar laboratorio de entrenamiento.cmd`.
El personaje debe estar conectado en la sala y fuera de combate.

El aplicador valida primero el baseline sin mutarlo, respalda sólo el perfil
del escenario en E, publica la configuración, espera su validación dentro
de World y entonces retira la tentativa anterior e inicia la nueva. Comprueba
cuatro objetivos, cuatro servicios y el mismo PID de World. Si falla,
restaura el perfil y solicita recuperar la escena anterior; comunica cualquier
fallo de recuperación. No reinicia Zone ni cliente ni opera el stack habitual.
La publicación usa la API tipada del sandbox: estos JSON no se recargan por
simple escritura del archivo. Sólo se sustituye MechanicsSandbox después de
validar el perfil completo; no se recarga la configuración global de Game.

La configuración persistente vive en el runtime aislado. Las instalaciones
nuevas del sandbox usan este preset; el archivo fuente general sigue
desactivado y sin servicios por defecto. Los resets retiran únicamente las
referencias de actores creados por su propia sesión, nunca por radio/template.

## Especializaciones y reset

La interacción nativa abre la UI real y `CSSwapAbilityPacket` consume la
elección por `CharacterAbilities.Swap`, con su coste normal y sus validaciones.
No se añadieron grants, especializaciones ficticias ni una UI paralela.

El baseline nuevo conserva únicamente buffs originales no pasivos y recalcula
los pasivos desde el libro ACTUAL. Excluye los hijos BuffEffect, aunque su
flag Passive sea false, para no resucitar un árbol abandonado ni duplicar
sus hijos al reset. Usa PassiveBuff.Remove/Apply y el consumidor real de buffs.
El baseline de una sesión anterior a esta actualización se retira una sola vez
al aplicar el nuevo perfil.

El preflight rechaza antes de retirar estado los productores que aún no puede
reconstruir: pasivos concedidos fuera del libro, auras/transformaciones, ciclos,
triggers con destinos externos o efectos distintos de BuffEffect. Es una
frontera explícita; no demuestra cobertura de todos los pasivos retail.
Se conserva la brecha existente de CSSwapAbilityPacket, que no valida el NPC
leído del paquete; no se amplió ni se usó como bypass del sandbox.

El perfil de combate de esta herramienta selecciona `CombatProfile=true` y
excluye únicamente el pasivo369 del libro activo del personaje vinculado.
La fila almacenada permanece intacta: `CombatProfile=false` recupera el libro
original en la próxima conexión. Se filtran tanto la carga guardada como
AddBuff, por donde pasa la concesión automática. Cuenta, ID y nombre deben
coincidir; un runtime con sandbox desactivado no aplica esta selección.

Esta selección es una decisión explícita del personaje de prueba, no una
clasificación retail «NPC-only». El usuario pidió orientación y se le explicó
esta elección de combate antes de aplicarla. La evidencia real es369→26210→Started25267→Timeout
SpecialEffect44787/SkillUse42427→plot4364, que contiene daño, spawn y otros
buffs; no se permite esa cadena como cleanup. Dossier en
`services/PASSIVE_369_BLOCKER_es.md`. No se alteran los datos ni el autogrant
del personaje original o de los demás actores.

Un fallo de preparación posterior a ENTERED_WORLD conserva ahora el cliente
conectado y retira su panel; los rechazos se comunican inmediatamente. Se
eliminó el caso que esperaba240s y después terminaba una sesión ya válida.

## Evidencia y límites de aceptación

Directorio forense:
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-custom-20261029`.

- `arena/REPORT.md`: mapas, sectores, spawns y decoración; 178 payloads con hash.
- `services/REPORT_es.md`: flags, prioridad de diálogo, packs, localización,
  82 assets/iconos y 35 dependencias directas CHR/MTL presentes. No implica
  clausura transitiva de todas las texturas ni render aceptado.
- `rea/catalog-full-c.manifest.json`: proyección acotada y reproducible de
  filas completas de doce tablas, desde la SQLite full abierta sólo lectura.
  Fuente SHA87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f;
  proyección 24039424 bytes, SHA526e7ddcb91af82585e78acaa9c6f656acd402a4f304366b893013fcf23aa674.
  Una segunda exportación produjo el mismo hash. No es la DB completa.
- `rea/npc-role-evidence.json`: REA6.8.0 inspect_sqlite_database real, SQLite3.53.4,
  evidencia `ev_5202271487335596228ef1c00c862f5fdb44614181f987eb2c06b1a347243c81`.
  Los cinco campos inspeccionados confirman los roles de los cuatro NPCs;
  no prueban interacción en vivo. La SQLite full excede el presupuesto256MiB
  del proveedor, por eso se usó la proyección trazable y no se elevó el límite.

No se tomó el escritorio; el usuario abrió el acceso habitual y el lanzador del
producto abrió su copia del cliente. Confirmó la entrada, los cuatro puestos
correctamente colocados y sus menús. Cambió Magic→Wild con Toosten y confirmó
tras el reset que conservaba la especialización y podía moverse sin reconexión.
World3626, cliente30576, Zone7644 y los dos sockets Game/Stream permanecieron
iguales; ZoneUnitCount9 después de recrear los ocho actores. Evidencia detallada
en `reconstruccion_cliente_10/checkpoints/CHECKPOINT_SANDBOX_TRAINING_HUB_20261029.md`.

Pruebas finales del código: build Release sin errores, 8906 tests .NET y 64
tests Python correctos. Los primeros cinco fallos de los tests nuevos se
debían a fixtures con BuffKind=0, un valor inválido; se corrigieron los
fixtures a Good y se repitió la suite completa. Logs bajo
`runtime/sandbox-aa10/temp/custom-hub-{build-final-combat,tests-combat,python-tests}.log`.

La publicación inicial del consumidor de perfiles añadió una sobrecarga de
constructor: dotnet watch informó ENC0011 y reinició World (PID240→3626).
En ese momento no había cliente conectado. El reinicio requirió cargar
datos antes de admitir la entrada; no se presenta como Hot Reload sin
reinicio. El lanzador ahora anuncia la espera y su progreso cada15 segundos.
La alternativa de ordenación del panel tras WinError5 sólo recoloca su
propia ventana y no usa un HWND externo como ancla después del rechazo;
su aceptación visual posterior sigue siendo una prueba del usuario.
