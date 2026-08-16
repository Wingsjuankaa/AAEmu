# AA10 r575 — entrega directa de items para pruebas

Fecha: 2026-08-16

Target: `Wingsjuankaa/AAEmu:rama_10`

## Objetivo

Entregar materiales, equipos y kits directamente al personaje de prueba sin
controlar su teclado, reiniciar el servidor ni insertar filas manualmente en
MySQL.

## Flujo confirmado

`AAEmu.Game` ejecuta un Web API interno en `*:1280`. Su
`CommandController` expone `POST /api/commands/{command}` y resuelve el
personaje online antes de llamar a `CommandManager`.

Para entregar items se usa `POST /api/commands/item` con argumentos equivalentes
a:

```text
/item add self <templateId> <count>
```

No es una mutación directa de base de datos. La ruta real es:

```text
Web API local -> CommandManager -> ItemAddSubCommand
              -> ItemManager/Bag.AcquireDefaultItem(ItemTaskType.Gm)
              -> persistencia + actualización del inventario del cliente
```

## Herramienta reusable

La skill `aaemu10-native-reconstruction` incluye:

```text
scripts/give-test-items.ps1
```

Ejemplo:

```powershell
$tool = "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\give-test-items.ps1"
$ids = @(44681..44716) + @(45090, 45091)
& $tool -Character Wingsjuanka -ItemId $ids -Count 20
```

El helper acepta `-Grade` cuando la prueba exige un grado específico. Omitirlo
mantiene el comportamiento por defecto de `/item add`; para Arcane usar grado
`4`, confirmado por `ItemGrade` y el catálogo r575:

```powershell
& $tool -Character Wingsjuanka -ItemId @(45338..45344) -Count 1 -Grade 4
```

El script:

1. exige que `aaemu10-game-1` esté activo;
2. consulta los personajes online;
3. exige una coincidencia exacta del nombre;
4. elimina IDs duplicados;
5. ejecuta una entrega por template y detiene el lote ante el primer error;
6. admite `-WhatIf` para revisar lotes sin mutar el inventario.

## Evidencia de aceptación

El 2026-08-16 se entregaron a `Wingsjuanka` 20 unidades de cada una de las 38
Lunagem `Glorious` con estadísticas visibles en `C`:

```text
44681..44716, 45090, 45091
```

El Web API respondió sin `ErrorMessages` en las 38 operaciones y el cliente
mostró las 38 pilas inmediatamente; el inventario quedó en `61/100`.

Los IDs se resolvieron desde el compact retail AA10 r575. Las `Sunglow` y
`Evenglow` se dejaron fuera de este lote porque modifican habilidades o duración
de controles, no filas directas de la ventana `C`.

## Reglas y seguridad

- Verificar IDs, cantidades, `max_stack_size`, restricciones y espacio libre
  antes de entregar un lote.
- Usar el endpoint sólo para preparar pruebas; no para ocultar defectos en una
  mecánica o reemplazar su transacción real.
- No escribir directamente en `items`/inventario MySQL mientras el personaje
  esté online.
- No publicar ni tunelar el puerto `1280`: actualmente el endpoint no tiene
  autenticación. El overlay AA10 lo mantiene sin `ports:` y se accede sólo con
  `docker exec` dentro de `aaemu10-game-1`.
- Si el endpoint necesita exposición remota, implementar autenticación,
  autorización y auditoría antes de abrirlo.
