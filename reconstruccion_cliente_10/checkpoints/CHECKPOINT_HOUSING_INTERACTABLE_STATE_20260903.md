# Housing: estado de puertas y ventanas — auditoría 2026-09-03

## Resultado y alcance

**Relog validado; persistencia nativa tras reinicio sin resolver. No se cambia runtime.**

El usuario confirmó el 2026-09-03 que la puerta y las dos ventanas abiertas con
Dannia siguen abiertas al hacer sólo relog, sin reiniciar Game ni Zone.
La hipótesis de pérdida de estado por logout queda descartada para esta prueba.
El reinicio de Game sí recrea estos bindings en su fase inicial según el código
actual. Esto explica el síntoma entre despliegues, pero no demuestra por sí solo
una divergencia respecto del servidor original.

No extender `PersistMutableState` a puertas/ventanas por inferencia. No se ha
probado que `force_db_save=false` signifique «nunca guardar», ni que la ausencia
de temporizador signifique «guardar a través del reinicio». Son contratos distintos.
Se corrige así la afirmación demasiado amplia del checkpoint H3 de que sólo
`force_db_save=true` puede conservar fase en DB. Para puertas queda **unknown**;
la decisión separada de H5-B sobre cultivos no se revierte ni se generaliza.

Target consultado: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`,
HEAD `ac4f3ecb2b3d2b996e74e75509055cc3e593a3c7`.
Padre consultado: `upstream/client_version/zone-10.0.2_r575`,
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. No merge ni actualización de código.

## Caso reproducido

- Personaje Dannia, character ID 1007.
- Casa DB 16, template 437 (Tradesman's Manor).
- Puerta template 4566, attach 36, objeto 101011.
- Ventanas template 4568, attach 37/38, objetos 101012/101013.
- Registros: apertura 2026-09-04 00:26:09–00:26:14 UTC;
  reentrada de Dannia 00:35:41–00:35:47 UTC, misma instancia de Game.
- Game sigue iniciado desde `2026-09-04T00:09:11.864394709Z`, RestartCount=0.
- Imagen sin cambios: `sha256:b8992f44d6b1d3ae26a19aca94a247c9520e7760d884ee3eb489c33d1ab34c35`.

## Evidencia de datos

Las siete consultas del auditor (bindings, templates, grupos, funciones de fase,
funciones de uso, timers, animaciones) coinciden íntegramente en full, compact
retail y compact montada del servidor. Sin discrepancia de datos en este alcance.

| Componente | Cerrado | Abriendo | Abierto estable | Cerrando |
|---|---:|---:|---:|---:|
| Puerta 4566 | 11163 | 11164 | 11165 | 11167 |
| Ventana 4568 | 11171 | 11172 | 11173 | 11174 |

Los cuatro timers 4196/4198/4202/4204 duran **1600 ms**: completan animaciones
de apertura o cierre. Las fases abiertas estables sólo ejecutan `DoodadFuncAnimate`;
el cierre sale de una interacción `DoodadFuncUse` con skill 16828. No hay transición
automática de cierre en esas fases. `delete_when_not_exist_creator`, `reset_data`
y `force_tod_top_priority` son false. Los campos generales min_time/max_time no
son un timer de cierre en este grafo.

Bindings 2386/2475/2564: `force_db_save=f` en las tres fuentes.
Catálogo H5-B: tampoco tienen `PersistMutableState`.

SHA-256 de inputs:

- Full: `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f`.
- Retail compact: `f61b6b6ed23ad83403d0e45f7d72f7cdf33553bcde03535e800acbb84639165b`.
- Server-observed compact: `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
- Zone `x2game-dev_dedicate.dll`: `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`.

## Frontera nativa revisada

Proyecto Ghidra Zone y DLL operacional tienen el mismo hash completo, arquitectura
x86-64, image base `0x39000000`. No se trasladan RVAs del cliente release ni AA8.

- Loader `FUN_39beaa50`, RVA `0xBEAA50`: consulta explícitamente
  `id, attach_point_id, doodad_id, force_db_save, housing_id`.
  Guarda registros de tamaño `0x14`: id+0, attach+4, doodad+8, housing+0xC,
  flag de `force_db_save` en bit 0 de +0x10. Acepta T/t/1 como true.
- Loader de housings `FUN_39beb780`, RVA `0xBEB780`: asocia esos descriptores
  a cada housing mediante un vector en +0xD0/+0xD8/+0xE0.
- Búsqueda de referencias al almacenamiento +0xF040/+0xEFC0: 13 instrucciones,
  incluyendo carga/inicialización y dos coincidencias de stack no relacionadas.
- Búsqueda de símbolos `HousingDoodad`, `BindingDoodad`, `SaveDoodad`: sólo RTTI
  del almacenamiento `HousingBindingDoodadDesc`; no se cerró un consumer de guardado.
- Buscar la cadena `SaveDoodad` no dio resultados. Esto NO prueba ausencia de
  una función equivalente sin ese nombre.

**Límite:** los loaders prueban que el flag es nativo y cómo se carga. No prueban
la política completa de guardado/restauración de World/DB del servidor original.
No se ha localizado/cerrado ese consumer en esta auditoría.

## Código y persistencia observados

- `HousingBindingRuntime.Synchronize` reutiliza el binding existente sin asignar
  fase inicial de nuevo. `Configure` aplica ownership/transform, no resetea fase.
- Al arrancar, los bindings sin estado persistido pasan por `Create` + `InitDoodad`.
- `RequiresPersistentState` sólo activa `ForceDbSave || PersistMutableState`.
  `Doodad.Save` retorna inmediatamente cuando `IsPersistent=false`.
- Consulta read-only `doodads WHERE house_id=16`: sólo row 5, template 1918,
  attach 0, fase 7894; ninguna puerta/ventana persistida.
- `Doodad.Write` envía `FuncGroupId` actual al cliente; `WZCreateDoodadPacket`
  también lleva la fase actual y los cambios se relayan mediante `WZDoodadChangePhase`.
  La prueba retail de relog pasa, sin requerir un parche de resincronización.

## Corroboración externa

Se buscaron combinaciones de ArcheAge + doors/windows + logout/relog/restart/
maintenance/reset, además de consultas en los foros de ArcheRage. No se encontró
una fuente específica que describa la conservación del estado después de reiniciar
el servidor. **external_unresolved**, no evidencia de que el reset sea correcto.

Las [notas de ArcheRage 8.0](https://na.archerage.to/forums/threads/archerage-8-0-global-update-spelldance-patch-notes.11507/)
mencionan un cambio de icono de la skill de abrir/cerrar puertas. Corroboran la
interacción, pero no su persistencia. No se usan como prueba de la regla pendiente.

## Reproducción y gates

Auditor read-only: `reconstruccion_cliente_10/scripts/audit_housing_interactable_state.py`.
Ejecutar con `--output <archivo.json>`; no modifica SQLite ni MySQL.
Los tres inputs pasan `quick_check=ok` e `integrity_check=ok`.
Dos ejecuciones producen SHA-256 idéntico:
`934f8b25f4d71c6f30e8e64d82eb997598a1d1ded5fe24cc1947a3611c7c2aa4`.

Artefactos fuera de Git:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\housing-interactable-state-frontier`.
Incluyen ambos JSON y logs `zone-persistence-strings`, `zone-binding-loader`,
`zone-binding-consumers`, `zone-housing-loader`.
El gate de identidad está versionado como `Aa10HousingPersistenceIdentity.java`.

Es una auditoría acotada, no cierre de Stage 30 ni del corpus consolidado.
No hubo cambios de gameplay, SQL, cliente, compact o configuración; no corresponde
build/despliegue de Game. No se operó el lifecycle de ninguna Zone.

## Decisión pendiente

Para llamarlo reparación nativa falta cerrar el consumer World/DB o conseguir
una prueba controlada de la misma puerta antes/después de mantenimiento en una
referencia compatible. El relog ya quedó validado y no necesita reparación.

Alternativa: el usuario puede autorizar explícitamente conservar puertas y ventanas
tras reinicio como **mejora propia de persistencia**, no como reconstrucción nativa
confirmada. Esa decisión requeriría política acotada, pruebas, documentación y
despliegue; no congelar indiscriminadamente luces, timers, cultivos u otros doodads.
