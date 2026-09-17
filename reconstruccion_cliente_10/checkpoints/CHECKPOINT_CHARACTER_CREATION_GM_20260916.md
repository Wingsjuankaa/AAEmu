# Creación GM r575 — 2026-09-16

Target/branch `rama_10`; base `b22b3ccfcfb001d198b8046658b525943e1f56bf`.
Padre consultado `upstream/client_version/zone-10.0.2_r575`,
`b439e1cc0d4bb96647d11dcb76da61b0246a53e1`.

Clasificación `client-native`. La autoridad 101 introducida en `e533e88b6`
activa el bit 4 que exige editor en NewCharacter. Lectura no mutante del
cliente confirmó autoridad 101 y gate de editor falso. Restaurada autoridad
1 con permisos GM mantenidos en servidor; sin cambios de DB ni cliente.

Contrato y evidencia en `Docs/AA10CharacterCreationGmAuthority_es.md`.
Build Release correcto; suite 4.619/4.619. Game/World desplegado con respaldo;
Zones no operadas. Falta aceptación del usuario tras nueva sesión.
