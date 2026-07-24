# Implementación de Fase A — objetos y equipamiento AA8

## Resultado

La Fase A deja construido un candidato nativo y un backend preparado para
probarlo, pero no lo activa automáticamente. El runtime estable y Docker
permanecen sin cambios.

## Extractor

`extract_native_equipment.py` reconstruye la clausura alcanzable desde los
21.419 IDs positivos presentes en la compact descifrada:

```text
item
→ tipo concreto
→ holdable/wearable/slot
→ grado y durabilidad
→ unit modifier
→ equip set/item set
→ buff/proc
```

Las relaciones nativas se leen de `game11`. Dos correcciones importantes de
procedencia quedaron incorporadas:

- `equip_item_sets`: rango nativo `0x46BD05C`, 495 filas.
- `item_sets`: rango nativo `0x80B9A0F`, 247 filas.

El generador filtra filas obsoletas que no son alcanzables desde un `item`
activo y valida todas las claves internas de la clausura.

## Modelos y loaders

Los modelos de objetos consumen los campos AA8 recuperados para:

- requisitos y flags de creación/uso;
- grado fijo, gradable y grado máximo;
- sonidos, skills asociadas y restricciones;
- holdables, wearables y tipos concretos;
- durabilidad y escalado;
- sets, procs y modificadores dinámicos.

La creación calcula la durabilidad después de resolver el grado definitivo.
Una definición incompleta no puede degradarse silenciosamente a `Item`
genérico.

## Motor de equipamiento

`IEquipmentRuleService` produce un `EquipmentTransitionPlan` antes de mutar
contenedores. La regla central es:

- 2H y secundaria nunca pueden coexistir;
- la mano desplazada va a la bolsa sólo si hay capacidad;
- las mutaciones desplazadas y la solicitud original se anuncian en un único
  `SCItemTaskSuccessPacket`;
- los bonos se recalculan desde el estado final canónico;
- una solicitud desactualizada se rechaza y recibe un snapshot autoritativo.

`IEquipmentSyncService` puede resincronizar equipamiento, bolsa o banco según
el contenedor que no coincida.

## Protocolo

Las máscaras de las 32 posiciones se calculan desde la posición física real,
no desde el índice de una lista compactada. Esto se aplica tanto al snapshot
de personaje como a `SCUnitStatePacket`.

El byte `flags` leído y persistido por `Item` se utiliza también en la
serialización incremental. La prueba de regresión exige que snapshot e
`ItemAdd` envíen el mismo valor. `ItemUpdate` rechaza detalles mayores que los
128 bytes admitidos por el wire layout actual.

La acción AA8 `UpdateDetail` no utiliza prefijo de longitud: después de
`slotType`, `slot` e `itemId` transmite exactamente 128 bytes crudos. El primer
byte de ese bloque es `detailType`. El contenido es la unión interna de
detalles de `FUN_3991f540`, no el formato variable de `WriteDetails`: en
equipamiento la durabilidad está en `detail + 0x05` y `ScaledA` en
`detail + 0x3c`. Esta ruta es distinta de `Create`; añadir un `uint16 128` o
copiar el snapshot variable dentro del bloque desplaza los campos y deja el
objeto visualmente inválido hasta el siguiente snapshot completo.

La ruta incremental `Create` quedó confirmada en `x2game.dll` mediante
`FUN_39a55190 → FUN_39a532b0 → FUN_3991f930 → FUN_3991f540`. Su detalle se
serializa con la misma longitud variable del snapshot: primero `detailType` y
después únicamente los campos de ese tipo. El arreglo de 128 bytes observado
en el cliente es almacenamiento interno, no un bloque fijo del wire. Anteponer
una longitud `128` hacía que AA8 interpretara `0x80` como `detailType`, dejando
la durabilidad visual en cero hasta que un relog enviaba el snapshot completo.
La regresión ahora compara byte a byte ambos payloads y verifica explícitamente
que el primer byte de detalle de equipamiento sea el tipo `Equipment`, seguido
por la durabilidad.

## Cuarentena

`quarantined_items` conserva las 17 columnas originales, motivo, hash del
runtime, fecha de cuarentena y estado de restauración. La herramienta
`build_quarantine_transaction.py` sólo genera SQL para revisión:

- no abre MySQL;
- no normaliza ni reemplaza objetos;
- considera segura únicamente cobertura `complete`;
- trata `phase_a_candidate` como incompatible hasta su aceptación;
- incorpora un guard para abortar si cambió la población revisada.

El argumento explícito `--allow-phase-a-candidates` habilita únicamente una
ventana de staging: conserva candidatas estáticamente cerradas para probarlas,
sin promoverlas ni habilitar su creación general.

## Herramientas GM

- `/item8` consulta el catálogo, cobertura y cuarentena.
- `/equipment audit` muestra máscaras, posiciones físicas, durabilidad y
  conflicto 2H/offhand.
- `/equipment resync` reenvía el estado autoritativo.
- `/additem` aplica cobertura y grados nativos. En staging puede crear una
  candidata de Fase A dentro de un scope temporal exclusivo del comando GM;
loot y el resto del servidor continúan bloqueando esas definiciones.

Durante la ventana de validación integral, el contenedor `game` puede habilitar
`AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES=1`. La excepción sólo acepta
`phase_a_candidate`; nunca habilita `catalog_only` ni `blocked`, y debe
retirarse al cerrar staging.

## Verificación automática

- Solución compilada: 0 errores.
- Pruebas Equipment + ItemTask: 21/21.
- Suite completa: 100/100.
- Dos builds SQLite con SHA-256 idéntico.
- `quick_check=ok`, `integrity_check=ok`.
- Cero referencias huérfanas en la clausura habilitada.

## Bloqueo antes de activar

La activación requiere una ventana de prueba controlada:

1. respaldo MySQL;
2. cuarentena revisada;
3. cambiar la ruta de compact sólo para `game`;
4. probar loot, creación, durabilidad, reparación y todas las transiciones de
   manos;
5. probar relog y un segundo cliente;
6. promover las definiciones verificadas de `phase_a_candidate` a `complete`.

Si alguna aceptación falla, se restaura la compact estable y el respaldo. No
se utilizará información 3.0 como fallback.
