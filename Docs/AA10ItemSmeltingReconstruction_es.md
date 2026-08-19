# Reconstrucción AA10 r575 — Item Smelting

## Resultado

El backend de `Item Smelting` quedó reconstruido en `rama_10` desde el cliente
Returns 10.0.2.13 r575 y la SQLite autoritativa. Carga las recetas, acepta el
contrato nativo del controlador de encantamiento, valida los recursos, resuelve
el resultado y entrega el item mediante `SCItemSmeltingResultPacket` (`0xCF`).

La aceptación dinámica del 19-08-2026 demostró, sin embargo, que la pestaña no
está lista para publicarse: el cliente r575 selecciona la receta 29 para el
objetivo 40000 y esa receta referencia los outputs 43482/43489, ausentes del
catálogo `items` exacto. Por seguridad `itemSmelting` queda disponible como
feature experimental, pero desactivada por defecto.

La ventana se publica mediante `Feature.itemSmelting = 178`. No se implementó
el TODO histórico `SpecialEffect 151`: la skill retail 35525 tiene solamente un
efecto de animación y transporta la operación mediante el skill-object tipo 20.
Los usos de special effect 151 en la base pertenecen a otras skills y no son la
ruta del controlador Smelting.

## Identidad de la evidencia

| Fuente | SHA-256 |
|---|---|
| `game_decrypted.sqlite3` | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| `compact.sqlite3` runtime | `FB9273AE82F69FAFCF5FF94E2FF95D7BBCB29A3AD3F6502CAF05713251BAFDAF` |
| `x2game.dll` release | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |
| `game_pak` operativo | `4DC5F729D54A8976802C2282F8D27512136BDF2354CB6B1594AAC7E626CCA8EB` |

El dossier derivado está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-smelting-frontier`.
Incluye el inventario del `game_pak`, el Lua retail extraído y la inspección de
API Lua (13/13 símbolos resueltos y presentes en el binario exacto).

## Contrato nativo cerrado

- `X2ItemEnchant:SwitchItemSmeltingMode()` entra al modo 10.
- `Execute(count)` inicia la skill 35525 usando el catalizador como `SkillItem`
  y el item objetivo como `SkillCastItemTarget`.
- Skill-object tipo `20`:
  - `bool autoUseAAPoint`;
  - `u32 smeltingDescId`;
  - después viene el `inputDirection` común del cast.
- `smeltingDescId` identifica exactamente una fila de `item_smeltings`; no es
  una instrucción confiable y se vuelve a validar completa en el servidor.
- El selector retail `FUN_3998b9c0` encuentra esa fila comparando el tipo del
  target y la cantidad. Las recetas 1–4 conservan esa elegibilidad nativa pese
  a sus etiquetas históricas de prueba; no se aceptan si el target/count no
  coincide con la fila solicitada.
- El cuerpo de `SCItemSmeltingResultPacket` es exactamente:
  - `s8 result`;
  - `bool resultItemByMail`;
  - `s64 itemId`;
  - `s32 type`.
- El constructor anterior escribía un `s8` adicional inexistente. Fue retirado.
- El Lua retail `center_message_manager.lua` fija los resultados:
  `0=fail`, `1=success`, `2=great success`.

## Catálogo y resolución

- `item_smeltings`: 32 filas.
- `item_smelting_items`: 96 filas, tres resultados por receta.
- `item_smelting_probs`: 6 filas.
- Base probabilística: `10,000,000`.
- Los tres outputs se asocian por `item_smelting_id` preservando `ORDER BY id`.
  Ese orden es el mismo que consume el Lua: Great Success, Success, Failure.
- El grado efectivo del item respeta `items.fixed_grade` cuando el template no
  es graduable, igual que el resto del runtime AAEmu. `item_grade_id` permanece
  en el descriptor para reproducir la tabla nativa y la vista previa.

Las recetas 29–32 están incompletas en la fuente exacta: referencian los items
43482 y 43489, ausentes de `items`. El loader las marca inválidas y el executor
las rechaza antes de RNG, pago o consumo. Las recetas 1–28 tienen sus tres
templates de salida presentes.

## Transacción y validaciones

En el momento de `Skill.ApplyEffects`, antes del consumidor genérico:

1. se exige feature 178 activa y skill-object 20 válido;
2. se resuelve la receta y se comprueba que pertenezca a la skill recibida;
3. se vuelven a resolver por id el catalizador y el objetivo dentro de la bolsa;
4. se exige que el catalizador use la skill de la receta;
5. se comprueban cantidad objetivo, material set completo, proficiency,
   labor, moneda y capacidad final de la bolsa;
6. bajo el lock de la bolsa se paga, se consumen objetivo/catalizador/materiales
   y se adquiere el resultado preflighted;
7. el executor toma propiedad del consumo para impedir que la limpieza genérica
   queme un segundo catalizador;
8. se publican las mutaciones y el resultado `0xCF`; la labor se cobra una sola
   vez al finalizar la skill.

La ruta de correo que el paquete permite anunciar permanece fuera de alcance:
la reconstrucción actual rechaza `BagFull` antes de cobrar y siempre responde
`resultItemByMail=false`. No se inventó un contrato de mail sin evidencia de la
creación y adjuntos del servidor retail.

## Fixture estático de referencia

La receta 5 es el caso mínimo usado por las pruebas unitarias del backend:

- target: item 40000 x1;
- catalizador: item 43446 x1;
- materiales: item 31010 x2 e item 15632 x6;
- costo: 10,000 copper;
- labor base: 500, con descuentos normales de Alquimia;
- probabilidad: 30% Great Success, 70% Success, 0% Failure;
- outputs: 43445 o 43476 según el resultado.

No debe presentarse como ruta accesible desde el cliente hasta demostrar cómo
el selector retail distingue las familias duplicadas que comparten
`item_id=40000` y `amount=1`.

## Aceptación dinámica en cliente r575

La prueba autorizada se ejecutó con `Wingsjuanka` dentro de Western Hiram
Mountains, levantando únicamente `o_hirama_the_west_2`:

1. `Advanced Charm` (43446) abre correctamente `Gear Upgrade > Refine Lunagem`.
2. El objetivo 40000 activa la vista previa de Great Success, Success y Failed.
3. El cliente solicita `Superior Waveglow Lunarite` (31013) x2 y
   `Territory Pence` (40229) x60; ambos quedaron reconocidos como `2/2` y
   `60/60`.
4. Repetir con otro objetivo 40000 en grade 0 seleccionó la misma familia.
5. El segundo slot conserva la etiqueta histórica `Lunagem Polish`. El item
   43445 con ese nombre está marcado por el propio r575 como obsoleto y su uso
   concede 1,400 Honor; no se consumió ni se forzó dentro del slot.
6. La vista coincide con la receta 29 (`item_set_id=51`). Como 43482 y 43489 no
   existen en ninguno de los compact exactos inspeccionados, el servidor la
   rechaza antes de RNG, cobro o consumo. No se pulsó Confirm.

Resultado de aceptación: **preflight visual logrado, ejecución final bloqueada
por datos retail incompletos**. El feature debe permanecer apagado hasta cerrar
los dos templates o probar que la pestaña es un remanente retirado del cliente.

## Capturas

- `Docs/evidence/item-smelting/01_target_and_materials_ready.jpg`: objetivo,
  materiales completos y tres resultados posibles.
- `Docs/evidence/item-smelting/02_advanced_charm_tooltip.jpg`: objeto que abre
  la herramienta (`Use: Refine a Lunagem`).
- `Docs/evidence/item-smelting/03_lunagem_polish_tooltip.jpg`: evidencia de que
  el item homónimo está obsoleto y concede Honor en este cliente.

## Verificación estática

- solución completa: compila sin errores;
- suite unitaria: 1,350 pruebas, con pruebas nuevas para skill-object 20,
  fronteras RNG, feature gate y cuerpo exacto de `0xCF`;
- inspección Lua: 13/13 APIs resueltas y 13/13 vocablos presentes en el
  `x2game.dll` exacto.
