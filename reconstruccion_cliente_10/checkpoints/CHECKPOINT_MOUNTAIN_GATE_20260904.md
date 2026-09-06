# Quest9192: Protect the Mountain Gate, Return976 omitido

## Autoridad y diagnóstico

Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`.
Padre `upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. El padre y AA8 no tienen el
cargador nativo de destinos explícitos implementado aquí. Se preservaron los
cambios locales anteriores, incluyendo configuración y WorldLevel de otra tarea.

A las17:47:05 UTC el personaje usa skill39534 sobre doodad13294/obj101198.
SpecialEffect37103 (efecto71839) ejecuta Return976. Game registra destino ausente
y no traslada al personaje. El segundo efecto73161 sí acredita ObjInteraction1078;
tras las tres bajas y esa interacción, ConAutoComplete3273 completa9192.
No hubo teletransporte a otra instancia ni una nueva caída de Zone en ese momento.

La relación está confirmada en full, compact retail y compact runtime:
return_points976 tiene editor_name `metastasis_gate`. El archivo r575 extraído
del game_pak actual contiene:

```
game/worlds/main_world/level_design/zone/350/world_server/return_point.g
ReturnPoint_metastasis_gate
pos ( x 2447.45, y 2378.5, z 513.6 )
zRot 1.02974
```

`world.xml` fija zone350 `o_hirama_the_west_1`, origin(17,28).
Posición mundo: **(19855.45,31050.5,513.6)**, yaw1.02974 rad (~59°).
La esfera2807 nativa tiene centro local(2447.54,2378.86,506.922), radio10.
El destino está a6.6883m del centro, dentro de ella. ConAcceptSphere926 inicia
quest9115; su objetivo es cinema290, con buff23667 en el componente45987.
No se inventa ni fuerza la siguiente quest.

Evidencia en `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/mountain-gate-9192/`:
`catalog-and-destination.json`, logs, CSV de todos los ReturnPoint del pak y tres
archivos nativos extraídos. Reproducir con `scripts/audit_mountain_gate_9192.py`.

## Corrección

`PortalManager` sólo unía posiciones nativas a return_points vinculados a Memory
Tomes. Ahora mantiene un índice separado para destinos explícitos de Return,
uniendo nombres únicos de SQLite con posiciones `return_point.g` de main_world.
Respeta offsets y orientación de Zone; rechaza nombres ambiguos, ubicaciones
conflictivas, origen desconocido y coordenadas no finitas.

El resolvedor conserva prioridad de worldgates/recalls existentes y después usa
el índice nativo. No introduce estos destinos en el libro, distritos o descubrimientos.
No cambia requisitos, objetivos, recompensas, paquetes ni lifecycle de Zone.
Tampoco cambia SQLite, game_pak ni worldgates.json. El transporte Return existente
se mantiene: mismo main_world usa SCTeleportUnit, sin SCLoadInstance redundante.

## Validación y despliegue

- Restore y build Release correctos; suite1806/1806. Dos pruebas nuevas cubren
  la posición/orientación976, separación del libro, datos ausentes, conflictos e idempotencia.
- Imagen `sha256:dd9bab5b6df5beb5d8c949117fb99b4e925fac7a145e284596462ed5efad0aaa`.
- DLL Game en ambas ubicaciones:
  `0157f88e98a602d89c3ac80b293d334ee62b3e8780add9b5ced342307c3570e9`.
- Rollback `aaemu-world:rollback-pre-mountain-gate-20260904` conserva imagen56103bb4…
- DB y compact respaldados en `E:/AAEmu/rama_10/backups/mountain-gate-20260904/`.
  DB SHA256 `a7c9be27eb956a78f1fa84e15af4c05e295957225c52356f1860274fe3ece032`.
  Compact SHA256 `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
- Sólo Game recreado con compose canónicos; DB/Login, mounts y puertos preservados.
  No se inició ni relanzó ninguna Zone. Arranque/índice efectivo registrados en manifest.json.

## Estado anterior y aceptación

El usuario completó9191, luego9193 y9192: se confirma aceptación del arreglo de Alcos.
Su9192 ya está completada y el portal deja de ofrecer su interacción de progreso
tras reconectar. Recuperación puntual, con Zone350 activa, mediante el comando
existente `/move 19855.45 31050.5 513.6`. Usa la ubicación nativa del salto perdido
y la aceptación normal por esfera; no reinicia9192 ni duplica sus recompensas.
No se modificó posición ni quests directamente en MySQL.

Aceptación retail del salto y cinema290 pendiente; pruebas de catálogo y servidor
no equivalen a completar la cinemática. El usuario controla el arranque de350.
