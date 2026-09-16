# Acceso alpha por cuenta — 2026-09-15

## Resultado

Solicitud del usuario: autorizar una cuenta para que todos sus personajes,
incluidos los creados posteriormente, accedan al panel alpha sin registrar sus nombres.

- Cuenta `wingsjuan`, ID 5, creada previamente en esta tarea; contraseña verificada
  con el formato del launcher. No se almacena aquí ni en la distribución.
- Migración aditiva `SQL/updates/2026-09-15_aaemu_game_private_alpha_account_access.sql`.
- Permiso concedido mediante `Scripts/Set-PrivateAlphaAccess.ps1 -Account wingsjuan -Action Grant`.
- La misma consulta de autorización backend resuelve el propietario persistido del
  personaje y acepta permiso de cuenta o permiso individual. Excluye personajes
  inexistentes y eliminados. La feature global sigue siendo obligatoria.
- La entrega de la llave opcional ya no crea permisos individuales permanentes.
  Revocar la cuenta bloquea la siguiente operación de los personajes que sólo
  heredaban acceso, aunque conserven la llave o la ventana abierta.
- Se conserva el permiso individual de Dannia, ID 1007, sin cambiar su fecha.
- El comando GM de revocación individual informa cuando persiste acceso por cuenta.
- Sin privilegios GM nuevos, cambios de protocolo, cliente, inventario ni monedas.
  El cliente LAN ya distribuido consulta este mismo backend.

## Administración

Desde `E:\AAEmu\rama_10\server\AAEmu`:

```powershell
.\Scripts\Set-PrivateAlphaAccess.ps1 -Account wingsjuan -Action Grant
.\Scripts\Set-PrivateAlphaAccess.ps1 -Account wingsjuan -Action Revoke
```

El permiso individual es independiente: `-Character Dannia -Action Grant|Revoke`.
No se necesita reiniciar Game para cambios de permisos posteriores a este despliegue.
El HUD consulta a los 1,5 segundos de entrar y cada 30 segundos; toda operación
económica comprueba permiso vigente. Las cuentas deben existir y ser únicas.

## Validación

- Restore y build Release completos: correctos, 0 errores; avisos de dependencias
  y analizadores existentes registrados en los logs.
- Suite unitaria: 2862 pruebas correctas, 0 errores, 0 omitidas; incluye tres
  pruebas nuevas de herencia, futuros personajes, revocación y cambio de propietario.
- `Tools/AlphaAccountAccessProbe`: 12 comprobaciones contra MySQL con tablas
  TEMPORARY de conexión, invocando el repositorio de producción. Pasa en host y
  dentro del contenedor contra la DLL desplegada. No crea personajes reales.
- `Tools/AlphaAccessProbe`: acceso individual de Dannia conservado, usuario ajeno
  rechazado y feature deshabilitada rechazada; consultas de sólo lectura.
- Migración y concesión repetidas: idempotentes. Cuenta 5 autorizada una vez;
  permiso individual 1007 conserva `2026-09-11 19:23:59`.
- La cuenta aún tiene 0 personajes: aceptación visual del panel pendiente de crear
  uno y entrar desde el cliente LAN. No se atribuye esa prueba a los probes.

## Despliegue y evidencia

- Target `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`.
- Padre `upstream/client_version/zone-10.0.2_r575`,
  `d892934591b7a52ee082a5f9a23b277d074d043d`; sin integración.
- Imagen nueva `sha256:a053dad762ac050d8328e5ee147ca9df918988a23d5c5ed846a2651985029578`.
- Contenedor Game iniciado `2026-09-16T01:26:54.521119885Z` (15 de septiembre local).
- Ambas copias de `AAEmu.Game.dll`:
  `498514cbc91afde9e6067316908b275d6079e411246fe57c3a0535e359012850`.
- `PrivateAlpha.json` montado y habilitado:
  `25b8ddcad6c038059e1036c6ae0621f7e8909825cd1f9c166efa64c45d68877d`.
- Evidencia local: `E:\AAEmu\rama_10\artifacts\alpha-account-access\20260915`.
  Incluye fuentes anteriores, permisos antes/después, logs y probes sin contraseñas.
- Se recreó exclusivamente Game; no se operó el lifecycle de Zones, Login ni DB.
  Los cambios previos del workspace se conservaron.
- Startup completado `01:28:36 UTC`: Game 1239 y Stream 1250 escuchando,
  registro en Login correcto; contenedor healthy, sin reinicios ni OOM.
  Gate de quests Strict: 43696 actos, 0 hallazgos. Sin errores de alpha.
  Persisten únicamente los cuatro errores conocidos de Item Smelting 29–32,
  excluidos del alcance; no se afirma un arranque global libre de errores.

## Rollback

Imagen anterior conservada como `aaemu-world:before-alpha-account-20260915`,
`sha256:192c3b4198dcbd8fbd604148087ee31c4d6abd4ae80c87f5c00da50d890b0d4a`.
Antes de restaurar comprobar que Game continúa usando la imagen nueva indicada arriba;
si hubo otro despliegue, revisar sus cambios antes de reemplazarla. Retaggear la imagen
anterior como `aaemu-world:10.0.2.13-r575-local` y recrear únicamente Game con
`docker compose -p aaemu10 -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml up -d --no-deps --no-build game`.

La tabla nueva es compatible con el backend anterior, que la ignora. No eliminarla
ni borrar otras cuentas. Para retirar sólo la autorización solicitada, ejecutar
`Set-PrivateAlphaAccess.ps1 -Account wingsjuan -Action Revoke`; no borrar la cuenta
ni sus futuros personajes. Las copias `*.before` son referencia para revertir
únicamente este cambio de código, conservando trabajo posterior.
