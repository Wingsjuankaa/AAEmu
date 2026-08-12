# Checkpoint — Auramancy nativa V1

Fecha: 2026-08-11
Cliente: Kakao `8.0.3.12 r558734`
Base: Shadowplay V6 `01088F98...6BAD3`

## Resultado del candidato

- runtime `7F4D3038...2E1469D`;
- 25/25 raíces habilitadas;
- 12/12 activas visibles;
- 13/13 ancestrales;
- seis pasivas;
- cero cuarentenas;
- `quick_check=ok`, `integrity_check=ok`;
- dos builds byte a byte idénticos.

## Autoridad y límites

AA8, Stage 15 y las relaciones exactas de la knowledge SQLite son autoridad.
Modern no aportó balance. AA10 sólo materializa la fila padre tombstone de
Teleportation tras la prueba viva de identidad y el gate del crosswalk.

La promoción de Conversion Shield no declara HealEffect globalmente cerrado:
se limita al consumidor AA8 con `event_id=9`, `use_damage_amount=1` y fixed
per-mille. No se añadió código por ID.

## Evidencia automática

- validador Auramancy: `6/6 PASS`;
- .NET Core 3.1: `633/633 PASS`;
- Mechanics Lab:
  - Teleportation: PASS, `SCSkillFired -> SCUnitBlink -> SCSkillEnded`;
  - Conversion Shield: PASS, daño mágico seguido de `SCUnitHealed`;
  - Vicious Implosion: PASS de cierre plot sin excepciones;
  - Battlerage Charge: PASS;
  - Behind Enemy Lines Gale: PASS;
  - Shadowplay Poisoned Weapons: PASS.

## Estado

El candidato está listo para aceptación viva. Auramancy se declarará cerrada
después de probar bases, pasivas y ancestrales en el cliente, además de
Flamebolt, Endless Arrows, Charge y Poisoned Weapons en la misma sesión.

## Supersesión V2 — 2026-08-11

V1 queda conservada como evidencia negativa y no debe desplegarse: el upsert de
filas con shapes distintos anuló campos server-only de once raíces visibles.
V2 separa Teleportation del lote AA8, preserva exactamente el carrier y exige
aprendibilidad explícita para las doce habilidades visibles.

- runtime: `A47153649ABAFC3F8DE0397F5B6192AD0ADE885A1FE77615B5CA211B23BAD84E`;
- `25/25` raíces habilitadas, `12/12` visibles aprendibles;
- `7/7` tests estructurales;
- dos builds byte a byte idénticos;
- compact montada en `game` con el mismo hash y `RestartCount=0`.
