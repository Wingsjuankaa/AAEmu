# Restauración de autoridad GM — 2026-09-18

Target/branch `rama_10`; base `6452af51397e83708af6cf3f65db23474c3d7add`.
Padre consultado mediante fetch explícito: `upstream/client_version/zone-10.0.2_r575`,
SHA registrado en el manifest adjunto. No se integraron cambios del padre.

## Resultado

Se retira localmente el envío incondicional de autoridad 1 propuesto en PR #1627.
`EnterWorldManager` vuelve a pasar el booleano de cuenta GM al paquete: acceso
>= 100 produce autoridad 101, y el resto autoridad 1, como el padre. El mismo
booleano conserva `gmFlag` del servidor. No cambian cuentas, personajes ni cliente.

El bit 0x04 autoriza al cliente GM y también exige editor al crear personajes.
Restaurarlo conserva ambas condiciones. No se inventa una excepción de creación
ni se asigna semántica a los bits 0x20/0x40 que ya enviaba el padre. Crear
personajes como usuario ordinario requiere una cuenta sin permisos GM.

El diagnóstico original acertó sobre la causa del bloqueo, pero su solución
confundió permiso del servidor con autorización del cliente. Se rectificaron
la documentación y el checkpoint original para evitar repetir esa conclusión.

## Evidencia y verificación

- `Docs/AA10CharacterCreationGmAuthority_es.md`: hashes, RVAs, alcance y límites.
- `E:\AAEmu\rama_10\artifacts\pr1627-review-20260918`: tres funciones nativas
  verificadas byte a byte, logs de restore/build/tests y build Docker.
- Restore correcto; build Release, cero errores (advertencias existentes).
- Suite completa: 5.464 correctas, cero fallos y cero omitidas.
- Pruebas de cuerpo del paquete: RSA y longitud conservados; GM conserva 0x04,
  cuenta normal no lo recibe y ambas conservan bit 0x01 para Stream.
- Esto no representa una nueva prueba de consola GM o idle kick dentro del juego.

## Entrega local

Imagen Game/World `aaemu-world:gm-authority-restore-20260918`, compilada Release
desde un contexto limpio de HEAD más los dos archivos fuente corregidos.
Respaldo previo: `aaemu-world:rollback-gm-authority-20260918`.
El manifest adjunto registra hashes de imagen/DLL y verificación de arranque.
No se operó el lifecycle de Zones; los servicios Login y DB se conservaron.
Se necesita una conexión nueva para recibir la autoridad restaurada.

Rollback de emergencia: etiquetar la imagen de respaldo como
`aaemu-world:10.0.2.13-r575-local` y recrear únicamente `game` con los dos compose
canónicos y `--no-deps --no-build`. Ese rollback restaura también el defecto de
autoridad 1; no debe usarse como solución permanente.

El [análisis publicado en #1627](https://github.com/AAEmu/AAEmu/pull/1627#issuecomment-5736900438)
solicita cierre de la propuesta upstream. Esta corrección se entrega en la rama
local; no modifica el PR retirado.
