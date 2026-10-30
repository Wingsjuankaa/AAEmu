---
name: aa10-es-es-localization
description: Localiza ArcheAge Returns 10.0.2.13 r575 al español internacional como distribución es_ES reproducible. Úsala para inventariar, traducir, revisar, empaquetar o probar textos, Lua/ALB, imágenes y mensajes de AAEmu conservando contexto, terminología, parámetros y trazabilidad.
---

# Localización AA10 es_ES

Trabaja sobre `E:\AAEmu\rama_10` y guarda el proyecto de traducción en `E:\AAEmu\rama_10\localization\aa10-es-es`. Aplica también `aaemu10-native-reconstruction` cuando la tarea toque el cliente, servidor o despliegue r575.

## Contrato del producto

- Presenta el producto como `es_ES` y escribe español internacional claro.
- Cliente principal desde el 2026-09-06 por decisión del usuario: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`. Usa este destino para traducciones, parches, arranque y pruebas; conserva sus cambios existentes.
- Mantén `ArcheAge-Returns-10.0.2.13-r575` intacto como referencia original. `ArcheAge-Returns-10.0.2.13-r575-es_ES` es el piloto histórico, no el destino operativo predeterminado. Una reconstrucción desde la base debe reaplicar los parches vigentes del principal.
- Usa internamente `+locale en_us`: el binario r575 no registra un locale español, aunque SQLite contenga una columna `es` vacía.
- Sustituye el canal `en_us` solo dentro de la distribución española. Usa `es` para mensajes generados por AAEmu cuando su cobertura esté aprobada.
- Mantén las voces originales; localiza texto y subtítulos.
- No abras una compatibilidad mediante parche del enum de locales mientras funcione el canal `en_us` reutilizado.

## Flujo obligatorio

Para comprobar textos, tooltips, NPCs y cambios relacionados en el laboratorio
existente, leer [sandbox-validation.md](references/sandbox-validation.md).
El sandbox usa una copia española privada y entrada automática aZone411.
Las operaciones de servidor y Hot Reload C# pertenecen a
`aaemu10-native-reconstruction`; no se confunden con recarga de ALB/paquetes.

1. Lee el manifiesto, las decisiones y el glosario del proyecto antes de traducir.
2. Identifica cada unidad por `(tbl_name, tbl_column_name, idx)` y por sus relaciones. Nunca uses solo el ID numérico o el texto inglés como identidad.
3. Reúne el contexto del consumidor, entidad, cadena de misión o flujo de interfaz. Contrasta `en_us` con coreano, chino, francés, alemán y ruso cuando haya ambigüedad.
4. Registra una decisión terminológica antes de propagar un término nuevo.
5. Traduce verticales completas: un flujo de UI, una habilidad con sus buffs, o una cadena de misión con NPC, objetos y diálogos.
6. Ejecuta QA estructural y lingüístico antes de cambiar el estado a `reviewed` o `approved`.
7. Genera compact/Lua/ALB/imágenes desde las unidades aprobadas. No edites el artefacto final como fuente de verdad.
8. Aplica primero a una copia de trabajo, valida, empaqueta y vuelve a extraer. Guarda hashes, respaldo, dry-run y rollback.
9. Prueba visualmente en el cliente r575: acentos, `ñ`, `¿`, `¡`, saltos, recortes, números, teclas y actualización dinámica.

## Reglas lingüísticas

- Prefiere vocabulario neutral y consistente. Evita regionalismos y `vosotros`.
- Conserva nombres propios hasta demostrar su traducción canónica o aprobar una adaptación.
- Traduce la función, no el inglés defectuoso. Marca como `blocked` lo que siga siendo ambiguo.
- Conserva exactamente el multiconjunto de variables, códigos de color, etiquetas, escapes y marcadores de formato.
- Mantén números y porcentajes salvo que el consumidor demuestre que son parámetros localizados.
- No abrevies para hacer caber una entrada del paquete. Resuelve el empaquetado o el diseño de UI.
- No traduzcas términos bloqueados por el glosario de forma distinta sin registrar una nueva decisión.

## Memoria y estados

La fuente versionada son los JSONL del proyecto; `translation_memory.sqlite3` es un índice generado. Cada unidad guarda fuentes, objetivo, hashes, contexto, procedencia, confianza, notas y uno de estos estados: `untranslated`, `draft`, `reviewed`, `approved`, `blocked`, `obsolete`.

Una coincidencia exacta puede sugerir una traducción, pero no aprobarla para otra identidad semántica. Propaga automáticamente solo una decisión terminológica explícita o una unidad vinculada que haya pasado la misma revisión de contexto.

## Puertas de calidad

Rechaza una unidad o build si cambia variables o markup, contiene mojibake/NUL, rompe UTF-8, deja etiquetas desbalanceadas, introduce términos inconsistentes o altera columnas mecánicas. Reporta inglés y CJK residuales como hallazgos revisables, porque algunos nombres propios pueden conservarse.

Verifica `PRAGMA integrity_check`, hashes de tablas no localizadas, idempotencia y rollback. Para `game_pak`, mide `size + padding` de cada entrada. Si compact o ALB crecen más que su capacidad, implementa una reconstrucción o relocalización de entrada probada antes de distribuir; no trunques contenido.

## Referencias

- Lee [references/context-and-style.md](references/context-and-style.md) para contexto, estilo y glosario.
- Lee [references/technical-contract.md](references/technical-contract.md) para locale, SQLite, ALB y empaquetado.
- Lee [references/qa-checklist.md](references/qa-checklist.md) al preparar una revisión o build.
