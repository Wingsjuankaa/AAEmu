# Frontera forense Item Smelting

Política del proyecto consumidor (2026-09-03): **DEPRECADO / FUERA DE ALCANCE**
por decisión explícita del usuario. Conservar esta evidencia, pero no reabrir
auditorías ni reconstrucción automáticamente, incluso si cambian hashes o aparecen
fuentes nuevas. Sólo una petición explícita permite retomar los gates históricos.
Feature178 permanece OFF; no afecta otros sistemas de Lunagem/crafting.

La frontera cerrada está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-smelting-frontier`.
Su `README.md` registra fuentes, hashes, artefactos y hallazgos.

Decisiones que no deben redescubrirse mientras los hashes no cambien:

- feature bit 178, modo ItemEnchant 10 y skill 35525;
- skill-object tipo 20 = `bool autoUseAAPoint + u32 smeltingDescId`;
- `SCItemSmeltingResultPacket` 0xCF no tiene byte inicial desconocido;
- resultado Lua: 0 Failure, 1 Success, 2 Great Success;
- outputs por receta en orden de fila: Great/Success/Failure;
- `FUN_3998b9c0` resuelve receta comparando `item_id + amount`; el servidor debe
  revalidar ambos campos y no inferir un bloqueo de las filas 1–4 por nombre;
- probabilidad sobre base 10,000,000;
- 32 recetas/96 outputs/6 filas de probabilidad;
- evidencia negativa: items 43482 y 43489 ausentes, por lo que recetas 29–32
  no tienen cierre de templates.

Hashes de esta frontera:

- full SQLite:
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`;
- x2game:
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`;
- game_pak:
  `4DC5F729D54A8976802C2282F8D27512136BDF2354CB6B1594AAC7E626CCA8EB`.

Sólo si el usuario reabre la mecánica y cambia alguno, reanclar RVAs, volver a extraer los Lua relevantes y repetir
la inspección `lua-types.rc`; no transferir el ABI por nombre.

## Auditoría2026-09-03 (no aceptación jugable)

Scripts versionados en reconstruccion_cliente_10/scripts:
audit_item_smelting_availability.py y Aa10SmeltingSelectorAudit.java.
Cuatro fuentes exactas, dos builds JSON idénticos SHA256
0626fe423ad05610e3002b07f8998b0bdee1af9218d77f77ff3821552864e7a7;
quick_check e integrity_check OK. Salidas availability-20260903-a/b en frontera.
40000 ausente en ambos compacts retail;43482/43489 ausentes en las cuatro fuentes.
Corrección durable:35525→61510→SpecialEffect27384/type151, NO Anim34.
43445→37020→67866→31887/type100/value1=1400, descripción obsoleta.

Proyecto Ghidra contiene baseline2735819, no405242e vigente. Comparación de todos
los bytes de98B9C0(98),AF6140(58),121180(586) contra el PE vigente idéntica;
log selector-reanchored-20260903.log. No extender esa igualdad a todo el DLL.
Selector devuelve primera coincidencia item/count, no menorID garantizado ni grado.
Historia2017 corrobora remanente, sin demostrar fecha de retirada Returns.
No habilitar feature ni forzar recipe5; nueva autoridad de datos o decisión legacy.
