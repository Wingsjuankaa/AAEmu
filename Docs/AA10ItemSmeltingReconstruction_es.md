# Reconstrucción AA10 r575 — Item Smelting

## Estado vigente — DEPRECADO / FUERA DE ALCANCE (2026-09-03)

El usuario decide excluir Item Smelting de este desarrollo y omitirlo de aquí en adelante.
Se archiva su reconstrucción por el valor limitado de recuperar esta vía histórica de producción
de Lunagem frente al coste y las incertidumbres de datos/contrato. No es una mecánica nueva.

- Mantener `itemSmelting=false` (feature 178); no programar reparación, activación ni prueba retail.
- No contabilizar sus TODOs como deuda activa ni reabrir por nuevos hallazgos sin petición explícita.
- Conservar código, pruebas y evidencia histórica; no modificar Lunagem, socketing ni crafting.
- Cierre por decisión de alcance, **no aceptación funcional** ni prueba de retirada universal del juego.
- Siguiente punto activo del roadmap: Housing H2/H5-B.

Esta decisión sustituye todos los «siguientes gates» y solicitudes de decisión del historial inferior.
No se modifican ejecutables, datos o configuración ni se requiere despliegue/reinicio.

## Resultado histórico de implementación (no aceptado)

El backend de `Item Smelting` quedó reconstruido en `rama_10` desde el cliente
Returns 10.0.2.13 r575 y la SQLite autoritativa. Carga las recetas, acepta el
contrato nativo del controlador de encantamiento, valida los recursos, resuelve
el resultado y entrega el item mediante `SCItemSmeltingResultPacket` (`0xCF`).

La aceptación dinámica del 19-08-2026 demostró, sin embargo, que la pestaña no
está lista para publicarse: el cliente r575 selecciona la receta 29 para el
objetivo 40000 y esa receta referencia los outputs 43482/43489, ausentes del
catálogo `items` exacto. Por seguridad `itemSmelting` queda disponible como
implementación archivada y desactivada, fuera del alcance actual.

La ventana se publica mediante `Feature.itemSmelting = 178` y transporta la
operación mediante el skill-object tipo 20. **Corrección del 03-09-2026:** la
skill 35525 sí referencia `SpecialEffect 151`; la afirmación anterior de que
sólo tenía Anim34 era incorrecta. Cadena exacta: skill_effect48479 → effect61510
→ SpecialEffect27384 → type151. El backend actual ejecuta el servicio desde
`Skill.ApplyEffects`; esa decisión de implementación no prueba ausencia de151.

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

## Reapertura prioritaria después de ArchePass — 2026-09-03

ArchePass publicado en `e8afe436d92e6cd28dd3b64052d9112a9b78c11e`; se inicia
el punto4 del roadmap sin habilitar feature178. Padre exacto actualizado por
fetch:3cc280b, sin implementación de servicio Smelting transferible; AA8 sólo
tiene el TODO SpecialEffect. Se conserva la jerarquía nativa AA10.

### Diferencia full/compact comprobada de nuevo

| Hecho | Full autoritativa | Compact actual del cliente |
|---|---:|---:|
| Total items | 51010 | 39134 |
| Template40000, objetivo de las32 recetas | Presente, use_skill11322 | Ausente |
| Templates43482/43489 | Ambos ausentes | Ambos ausentes |
| Recetas con objetivo ausente | 0 | 32 |

Compact actual SHA256:F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B.
No equiparar este snapshot a los compact usados en las pruebas de agosto.
Sus textos localizados aún conservan40000 como Refined Lunagem: una traducción
residual no demuestra que exista el template. Full conserva la descripción
coreana de43445 que declara que ya no puede producirse/usarse y ofrece conversión;
el inglés runtime indica desuso. Su skill actual es37020, no35525.

Las8 referencias huérfanas corresponden a dos outputs por receta29/30/31/32.
Los28 registros anteriores tienen outputs existentes, pero esto no demuestra
accesibilidad por el selector real. No sustituir receta29 por5 en servidor ni
reinyectar40000 al compact sólo porque existe en full.

### Corroboración externa, no autoridad de implementación

Consulta2026-09-03. La [quest11302 de ArcheAge Codex US](https://archeagecodex.com/us/quest/11302/)
menciona Lunagem Polish, pero no documenta Smelting ni los dos outputs ausentes.
El [catálogo de crafting awen](https://archeagecodex.com/query.php?a=craft&l=awen&type=paper)
enumera43445 como Lunagem Polish; es otra proyección/locale sin buildr575 fechado.
Clasificación de ambas pistas:`external_unresolved`, no prueba de disponibilidad.
Las consultas directas de los items43482/43489 no fueron legibles por la
herramienta web; eso NO se interpreta como prueba de inexistencia en ese sitio.
La búsqueda por IDs tampoco aportó un contrato verificable de esos templates.

### Decisión y siguiente gate

Mantener `itemSmelting=false`, verificado en fuente, bind mount y contenedor.
Estado: investigación iniciada, ejecución retail bloqueada por evidencia de
datos/proyección, no por un TODO que baste con activar. No hay cambio de runtime
que desplegar ni necesidad de reiniciar Game en esta reapertura.

Siguiente gate: identificar una fuente exacta que resuelva43482/43489 y la
proyección/selección del objetivo40000, o demostrar documentalmente la retirada
de toda la pestaña. La descripción de un item obsoleto no basta por sí sola.
Una implementación con sustituciones diseñadas sería variante custom, no una
reconstrucción nativa, y requiere decisión explícita. No se salta a Housing
automáticamente en este corte. Consultas reproducibles y manifest en la frontera.

## Auditoría ampliada y límite de continuación — 2026-09-03

**Estado: NO LISTO PARA PRUEBA JUGABLE.** No se declara cerrada la mecánica.
La auditoría está cerrada para las cuatro fuentes congeladas; no equivale a
demostrar que no exista otro snapshot exacto recuperable.

### Hechos reproducidos

| Fuente | Items | Objetivo40000 ausente | Outputs huérfanos | Tabla de probabilidades |
|---|---:|---:|---:|---|
| Full autoritativa | 51010 | No | 8 referencias,43482/43489 | 6 filas |
| Snapshot runtime full-derived | 51010 | No | Las mismas8 | 6 filas |
| Snapshot compact retail | 39134 | Sí, afecta32 recetas | Las mismas8 | No proyectada |
| Compact cliente actual | 39134 | Sí, afecta32 recetas | Las mismas8 | No proyectada |

La omisión de probabilidades en compact no prueba retirada: son datos de servidor.
La ausencia del objetivo en ambos compacts y de dos resultados incluso en full
sí bloquea esta aceptación. No es una pérdida provocada por el último despliegue.
Las cuatro fuentes contienen la cadena de35525→151 y43445→37020→67866→31887,
type100/value1=1400. El nombre coreano/descripcion de43445 declaran desuso y
conversión;43476 describe compra en Honor Shop.

### Selector reanclado, no RVA transferida a ciegas

El proyecto Ghidra conservado pertenece al hash2735819..., no al DLL vigente
405242e.... El primer gate de identidad rechazó esa atribución. Se compararon
después todos los rangos de código de tres funciones contra el PE vigente:

| RVA | Bytes idénticos | SHA256 del rango |
|---|---:|---|
| 0x98B9C0 selector | 98 | b1c6400efb70b33cf29a1f81085d754b226f3f20fc973871919a2608616e43e2 |
| 0xAF6140 iterador | 58 | cea0659fb784b20d173671dd4616c289885c18ba2f0b67193c4bde428a427bc9 |
| 0x121180 caller | 586 | 007bcd6819039f3b336e279ca79ab9e37913af1efe7e76723a4311135578f6e2 |

El selector devuelve la **primera** coincidencia por item y cantidad, sin grado,
color ni material set como desempate. El caller comprueba además `0x97=151`
en la ruta de skill. La igualdad local de código no certifica todo el binario ni
el orden de carga del catálogo. No se deduce que la primera fila sea el menor ID:
la captura histórica sigue siendo la evidencia de selección29. Por ello receta5
no es un kit retail que podamos entregar como funcional.

### Historia y clasificación corregida

La [descripción histórica del refinado de abril de2017](https://www.inven.co.kr/webzine/news/?news=176034&site=archeage)
documenta su existencia previa a AA10. La [crónica coreana del cambio de septiembre de2017](https://www.inven.co.kr/webzine/news/?news=186013&vtype=pc)
describe la supresión de las ramas éxito/gran éxito en la fabricación de tier2,
la compra de tier1 por Honor y la conversión del catalizador a1400Honor.
Estas fuentes secundarias corroboran la historia, no son autoridad de balance
Returns ni prueban una fecha exacta de retirada de esta build. No se obtuvo la
nota oficial original en las búsquedas realizadas. No se copian recetas externas.

Clasificación: **mecánica histórica post-lanzamiento, con datos residuales y ruta
r575 bloqueada**; no «nueva en AA10». La hipótesis de remanente retirado tiene
corroboración, pero no se promociona a prueba absoluta de retirada de toda la UI.

### Entrega y decisión requerida

Scripts versionados en `reconstruccion_cliente_10/scripts/`:
`audit_item_smelting_availability.py` y `Aa10SmeltingSelectorAudit.java`.
Artefactos: `item-smelting-frontier/availability-20260903-{a,b}/audit.json`
y visor `index.html`; ambos builds de datos SHA256
`0626fe423ad05610e3002b07f8998b0bdee1af9218d77f77ff3821552864e7a7`.
Cuatro `quick_check=ok` e `integrity_check=ok`; hashes de inputs comprobados
antes/después. Log nativo: `selector-reanchored-20260903.log`.

Continuar de forma nativa requiere una fuente exacta que cierre los templates,
la proyección y una ruta seleccionable. Restaurar contenido histórico mediante
otros snapshots o diseñar sustituciones exige autorización del usuario como
**restauración legacy/variante**, con manifiesto y balance separados de AA10.
No basta autorizar un reinicio o pedir «terminarlo» para inventar esos contratos.

Feature178 sigue apagada. No hubo cambios funcionales ni despliegue/reinicio en
esta auditoría; Zone, inventarios y monedas se conservaron. Los comentarios
erróneos del executor se corrigen sin alterar su comportamiento. No se anuncia
aceptación jugable ni se pasa automáticamente a Housing.
