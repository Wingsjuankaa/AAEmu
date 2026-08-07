# Checkpoint B13h — progresión de síntesis por `grade_order`

Fecha: 2026-07-31

## Síntoma observado

Dannia sintetizó `48023 Moonrise Jerkin` con una infusión de historia
`48845`. El cliente previsualizaba una transición hasta Arcane, pero el
servidor persistió:

```text
target=16777266/48023
material=16777262/48845
exp=50
grade=0->1
sectionExp=0->38
```

El ID `1` es Crude, por lo que el objeto fue degradado visualmente en lugar
de avanzar por la escala nativa.

## Causa probada

AA8 no ordena los dos primeros grados por su ID:

| `grade_order` | `grade_id` | nombre |
|---:|---:|---|
| 0 | 1 | Crude |
| 1 | 0 | Basic |
| 2 | 2 | Grand |
| 3 | 3 | Rare |
| 4 | 4 | Arcane |

El consumidor confirmado `LoadItemGradeOrder` de `x2game.dll` usa:

```sql
SELECT id FROM item_grades ORDER BY grade_order ASC
```

El backend recorría la síntesis mediante `gradeId++` y comparaba el límite
con el ID numérico. La previsualización del propio cliente corroboró la ruta
ordenada y el salto gratuito desde Crude, cuya fila tiene `grade_exp=0`.

Para la categoría Moonrise `635`, una infusión `48845` aporta `50 EXP`. Desde
Basic, la transición correcta consume `11 + 16 + 22 = 49 EXP`:

```text
Basic (id 0) -> Grand (id 2) -> Rare (id 3) -> Arcane (id 4)
sectionExp final = 1
```

## Reparación transversal

- `ItemEvolutionRuleService` registra el mapeo bidireccional
  `grade_id <-> grade_order` desde el catálogo AA8 cargado por `ItemManager`.
- Los límites de síntesis se comparan por `grade_order`.
- El avance toma el siguiente ID por orden, nunca mediante `gradeId++`.
- Un `grade_exp=0` intermedio avanza sin consumo; una propiedad ausente o una
  secuencia incompleta se rechaza en lugar de inventar continuidad.
- No se modificó la compact activa ni ninguna fila nativa.

## Validación automatizada

- pruebas dirigidas de síntesis: `7/7`;
- suite completa .NET Core 3.1: `314/314`;
- regresiones exactas:
  - `Basic id 0 + 11 EXP -> Grand id 2`;
  - `Crude id 1 + 49 EXP -> Arcane id 4`;
  - `48023 + 48845 (50 EXP) -> Arcane id 4, sectionExp 1`.

## Estado persistido y recuperación

Antes de la reparación:

```text
Dannia id=1
item instance=16777266 template=48023 grade=1 sectionExp=38
remaining infusion instance=16777261 template=48845 grade=2 count=1
```

Respaldo MySQL:

```text
D:\Proyectos\AAemu\backups\pre-point0-story-synthesis-grade-order-v1-20260731.sql
SHA-256 92087597931027FFE499C6AEE34245E37EAD838CDA3CECB0B333DA813A3B06D1
```

Compensación aplicada con `game` detenido: sólo la instancia `16777266` fue
modificada a `grade=4`, `sectionExp=1`, sin consumir otra infusión ni cobrar
otra vez. La instancia `16777261/48845` permaneció en cantidad `1`, grado `2`.

## Despliegue

- imagen anterior preservada como
  `aaemu-game:pre-point0-story-grade-order-v1-20260731`;
- imagen nueva:
  `sha256:6c5bc0b0b28848c86c69b92e1f5e6566aaa790f39c61792f28e52e954aaec660`;
- compact montada, sin cambios:
  `84a2e6af2b890a3fe066129f80f041dde2ff6b071b151ad0d05e2fb509073e0f`;
- sólo se recreó `game`; `db` y `login` permanecieron activos;
- `ScriptCompiler`: 0 errores;
- inicio: `00:01:44`, puertos `2239/2250` y registro en LoginServer;
- reinicios: `0`.

## Aceptación manual pendiente

1. Verificar que `16777266` aparezca Arcane con `1 EXP` persistido.
2. Abrir Gear Upgrade con otra pieza Basic y la infusión restante, sin
   confirmar todavía.
3. Confirmar que la previsualización y el servidor coincidan en Arcane.
4. Realizar una única síntesis, desconectar limpiamente y comprobar
   persistencia.
