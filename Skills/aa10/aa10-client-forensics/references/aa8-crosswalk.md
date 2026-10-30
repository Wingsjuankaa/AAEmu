# Crosswalk AA8 -> AA10 r575

Usar AA8 porque ambos clientes modernos son x64 y comparten gran parte del
motor, naming, tipos y familias de entidades. Tratarlo como acelerador de
búsqueda, no como autoridad.

## Candidatos reutilizables

- identidad estable y natural keys;
- nombres de tablas/campos y relaciones estructurales;
- RTTI, vtables y patrones de factories con firma corroborada;
- estados de lifecycle y primitivas transaccionales genéricas;
- assets o localización que AA10 confirme independientemente.

## Siempre version-sensitive

- opcodes, niveles, framing, cifrado, counters y layouts;
- offsets/RVA sin hash, tamaños y signedness;
- IDs retirados o añadidos, balance, rates, cantidades y fórmulas;
- cooldowns, cast/channel timings, probabilidades y AI;
- filas runtime, schemas y branches exclusivos de AA8.

Clasificar cada hallazgo como `aa10_confirmed_from_aa8_lead`,
`structural_candidate`, `version_sensitive_blocked`, `aa8_only` o
`conflict`. Promover sólo después de evidencia AA10 independiente.
