# Checkpoint: estado efectivo y transiciones ancestrales AA8 V2

Fecha: 2026-08-05 (America/Santiago)

## Fallos reproducidos

El personaje de aceptación `Dannia` quedó persistido en nivel normal 55,
Ancestral 1 y `2.329.599` EXP ancestral: exactamente
`heir_levels(level=1).req_total_exp - 1`. La interfaz mostraba 100%, pero no
emitió otro `CSHeirLevelUp (0x125)`. En la misma sesión, la UI mostraba las dos
variantes de Flamebolt, pero no permitió seleccionarlas y no emitió
`CSActivateHeirSkill (0x08F)`.

Los logs descartaron rechazos del handler: ninguno de los dos C2G llegó al
servidor durante el fallo.

## Causa de la variante Flamebolt

`CSSpawnCharacterPacket` emitía `SCListSkillActiveTyps (0x236)`, pero
`CharacterSkillActiveTypes.BuildPacketEntries()` serializaba únicamente los
overrides persistidos. Un personaje nuevo no tenía filas en
`character_skill_active_types`, por lo que recibía una lista efectiva vacía.

El catálogo AA8 montado conserva:

- Heir `19`, skill base `10752`, step `1`;
- sucesor `36474`, posición `1`, active type `1`;
- sucesor `36475`, posición `8`, active type `1`.

La SQLite descifrada AA10 r575 confirma el mismo Heir, ambos IDs, posiciones,
tipos activos y `active_item_id`. El crosswalk clasifica todavía las tablas
`heir_*` como `aa10_only` porque no estaban en la consolidada AA8 original; se
usó sólo para reducir el vacío y corroborar relaciones, no para reemplazar la
autoridad AA8 del runtime extraído de game11.

La lista G2C ahora materializa el estado efectivo de todas las familias
habilitadas hasta el step ancestral del personaje, aplica encima cualquier
override persistido y conserva los pares genéricos con Heir 0. El límite nativo
de 200 entradas sigue aplicado. Tras cada ascenso se reenvía el snapshot para
que un nuevo step sea visible sin reloguear.

## Causa y compatibilidad de la transición a Ancestral 2

El predicado nativo AA8 recuperado exige el límite exacto
`total_exp == req_total_exp - 1` antes de emitir el C2G vacío. Ese contrato se
mantiene para la entrada 0→1, cuya fila AA8 requiere `1 x item 40491`.

La sesión viva probó una frontera distinta: en 1→2 la fila no exige objeto y
el cliente quedó al 100% sin emitir el C2G. Para evitar un bloqueo permanente,
después de enviar el `SCExpChanged` que alcanza una frontera sin objeto el
servidor ejecuta el mismo `TryLevelUpHeir()` autoritativo. No se omiten las
validaciones de nivel, EXP derivada ni catálogo, y las fronteras con objeto
continúan esperando la solicitud y el consumo explícitos.

## Implementación

- `HeirGameData.GetSelectableHeirSkillsForStep()` expone el catálogo estático
  ordenado y limitado por step.
- `CharacterSkillActiveTypes.BuildPacketEntries()` combina defaults AA8 y
  overrides persistidos.
- `Character.ApplyHeirExpGain()` señala únicamente una frontera exacta sin
  objeto.
- `Character.AddExp()` completa esa transición después del paquete de EXP.
- `Character.TryLevelUpHeir()` reenvía el snapshot de active types tras subir.

No se editó MySQL, no se inventaron IDs y no se promovieron propiedades de
balance 10.x.

## Verificación

- pruebas focalizadas ancestral/protocolo: `17/17`;
- suite completa: `513/513`;
- build Docker Game: correcto;
- runtime montado verificado:
  `compact-8.0-runtime-honor-store-v1.sqlite3`, SHA-256
  `C9D7E78196CC2563DB61498B566E9785A1850D2D869E4878E22287E6A79BC258`;
- estado previo de aceptación: Dannia Ancestral 1, EXP `2.329.599`, cero
  activaciones Heir y cero overrides active-type.

## Aceptación viva pendiente

1. reloguear para recibir el snapshot efectivo;
2. ejecutar `/addexp 1` y comprobar transición inmediata a Ancestral 2;
3. abrir Ancestral y seleccionar sólo Flamebolt `36474`;
4. confirmar `C2G 0x08F`, `G2C 0x18C`, persistencia y un único cast;
5. luego cambiar a `36475` con `isChange=true` y repetir tras relog.

