# Entrega directa para pruebas AA10

Usar este flujo para entregar items de prueba sin controlar el teclado del
usuario, reiniciar el runtime ni modificar MySQL directamente.

## Contrato local

- `AAEmu.Game` habilita `WebApiNetwork` en el puerto interno `1280`.
- `CommandController` acepta `POST /api/commands/{command}`.
- Para items, el body contiene el personaje online y argumentos de
  `/item add`: `add self <templateId> <count>`.
- El comando pasa por `CommandManager`, `ItemManager`, `ItemTaskType.Gm`,
  persistencia y packets normales de inventario.
- El overlay AA10 no publica `1280`; invocarlo sólo con `docker exec` desde el
  contenedor `aaemu10-game-1`.

No publicar, tunelar ni exponer `1280` mientras el Web API carezca de
autenticación. Si se necesita acceso remoto, implementar autenticación y
autorización antes de abrir el puerto.

## Procedimiento preferido

Cuando AAEmu Control Center esté abierto, usar su pestaña administrativa para
entregas pequeñas y confirmadas: valida nombre, template, cantidad y grado,
ejecuta el comando dentro del contenedor y deja auditoría local. Para kits
grandes o repetibles conservar `give-test-items.ps1` como vía batch.

1. Resolver los `item_template_id` en la SQLite completa/compact r575; no usar
   nombres o IDs de AA8 como autoridad.
2. Confirmar el `max_stack_size`, restricciones y cantidad de slots libres.
3. Confirmar que `game` está saludable y que el personaje exacto aparece online
   en `GET /api/world/logged-characters`.
4. Ejecutar `scripts/give-test-items.ps1`; usar `-WhatIf` primero cuando el lote
   sea grande o su alcance no esté claro.
5. Detener el lote ante el primer `ErrorMessages`, template ausente o fallo de
   inventario. No compensar con inserts SQL.
6. Confirmar visualmente el inventario y, cuando la prueba lo requiera,
   persistencia después de relog.

El Control Center también consume `GET /api/character/{id}/inventory` y
`GET /api/world/chat-events`; ambos endpoints siguen siendo internos al
contenedor. Consultar
`E:\AAEmu\rama_10\server\AAEmu\Docs\AA10ControlCenterWebApi_es.md`.

Ejemplo:

```powershell
$ids = @(44681, 44682, 44683)
& "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\give-test-items.ps1" `
  -Character Wingsjuanka -ItemId $ids -Count 20
```

Para forzar un grado concreto, pasar `-Grade`; omitirlo conserva el grado por
defecto del comando. Por ejemplo, Arcane es `4` en AA10 r575:

```powershell
& "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\give-test-items.ps1" `
  -Character Wingsjuanka -ItemId @(45338..45344) -Count 1 -Grade 4
```

Kit de estadísticas `Glorious` usado el 2026-08-16:

```powershell
$ids = @(44681..44716) + @(45090, 45091)
```

Esos 38 templates afectan estadísticas visibles en `C`. Separar
`Sunglow`/`Evenglow`, que modifican habilidades o duración de controles y no
tienen una fila directa en esa ventana.

## Comprobación manual equivalente

El request interno equivale a:

```text
/item add self <templateId> <count>
```

Ejemplo de body para diagnóstico, no para exponer como API pública:

```json
{
  "character": "Wingsjuanka",
  "arguments": "add self 44681 20"
}
```

## Evidencia de aceptación: Replace Effects Hiram (2026-08-19)

Esta aceptación sirve como patrón de prueba para el lifecycle de Zone autorizado y para mecánicas
que tengan dos formas de pago. La autorización fue específica para iniciar o relanzar únicamente la
Zone de la posición persistida del personaje. La resolución produjo `zone_id=351` y perfil
`o_hirama_the_west_2`; se inició sólo:

```text
E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64\AAEmu.ZoneHost.exe +zone o_hirama_the_west_2
```

La aceptación exigió y obtuvo un solo `AAEmu.ZoneHost`, TCP establecido contra Game `:1240`,
`ZWJoin`, `WZJoinResponse`, `ZoneLoaded` y heartbeats posteriores. No usar este antecedente como
autorización abierta: cada task debe contener autorización explícita y debe volver a resolver la
posición actual antes de elegir el perfil.

Caso dinámico con cliente retail `10.0.2.13.KX r575`, personaje `Wingsjuanka` y
`Celestial Hiram Guardian Shoes` item `16777293`/template `45342`:

- Camino nativo sin piedra, skill `39836`, `SkillCasterUnit`, item target y skill-object `9`:
  `Stamina 60 -> Intelligence 60`, grupo `1234 -> 1235`, Change Attempts `3 -> 2`, piedras
  `46682` intactas en `3`; servidor: `payment=change-attempt, attempts=2`.
- Camino con `Bound Serendipity Stone` `46682`:
  `Intelligence 60 -> Strength 60`, grupo `1235 -> 1232`, piedras `3 -> 2`, Change Attempts
  intactos en `2`; servidor: `payment=item:46682, attempts=2`.

Criterios reutilizables: probar ambos pagos por separado; cruzar diálogo visual, inventario,
contador persistente y log de commit; comprobar que sólo se consume el recurso elegido. La imagen
Game desplegada fue
`sha256:668f202cf2268194b9154ed80cc3c9c17fcf194aa6ceec667907787c57523e48` y la suite Release
terminó `1329/1329`, sin errores ni pruebas omitidas. El dossier técnico completo está en
`E:\AAEmu\rama_10\server\AAEmu\Docs\AA10ItemEvolvingReRollLuaContract_es.md`.
