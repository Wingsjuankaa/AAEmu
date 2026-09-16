# Regresión transversal de inicio de habilidades — 2026-09-16

Target `rama_10`; padre integrado `b439e1cc0`. Regresión introducida por la resolución local de `CSStartSkillPacket` durante la integración (`c50ffacca`, publicada en `17be639b3`).

## Causa y cierre mínimo

El lector cambió el tratamiento de tipos desconocidos de SkillCastExtra de continuación a rechazo. `SkillObject.IsKnownType` omitía `None=0`; antes ese caso seguía con un objeto vacío y después retornaba antes de ejecutar la habilidad. El log sólo avisaba si el tipo no era cero. Los ataques, planeadores y objetos sin contexto adicional quedaban descartados silenciosamente.

Los registros del usuario contienen 29 entradas CSStartSkill y ninguna advertencia de tipo desconocido ni avance al log StartSkill en la ventana conservada. La prueba reproduce el rechazo con flags `00`, `40`, `80` y `C0`: los seis bits bajos son cero y los dos superiores son flags independientes.

Se reconoce `None` como tipo válido y se implementa explícitamente su lectura vacía, conservando el byte inputDirection para el paquete contenedor. Los tipos desconocidos siguen rechazados. No se cambian efectos, restricciones de inventario, cooldowns, catálogos ni mecánicas por ID. Clasificación: restauración del contrato existente, `server-required`.

## Verificación

- Antes: cuatro casos de contexto vacío fallan; tres tipos desconocidos se rechazan correctamente.
- Después: compilación Release y **4.599/4.599 pruebas** aprobadas; cero omitidas.
- Respaldo SQL tras parada normal de Game: `runtime-before.sql`, SHA256 `8dc8d931f8fbc92b7ec57dc2a692a7cfff2893829c20de38470276fcf02c5407`.
- Imagen previa: `b5c72b6362259317be72951cbcc7dd7aa09e220d30e3eb566bcbf9ea206dc41a`.
- Imagen corregida: `b5b521fab2dbeb8e692a041b16e7847ee4af77aa70d92aa3cfd6c7ba86fd2033`.
- Artefactos: `E:/AAEmu/rama_10/artifacts/item-regression-20260916`.
- Sin migración de datos. Cliente español, compact y ZoneHost conservados. Lifecycle de Zones a cargo del usuario.

Estado: Game/World/Stream iniciados, API responde y contenedor saludable sin reinicios; aceptación A/B dentro del cliente pendiente. Primer paso de aceptación: un ataque básico contra un objetivo válido; después un objeto y el planeador.


Confirmación posterior del usuario (2026-09-16): pudo entrar y volvió a disponer de acciones. Esto confirma la recuperación general de la respuesta, sin dar por validados individualmente ataques, daño, todos los objetos ni planeadores. Las pruebas específicas continúan pendientes.
