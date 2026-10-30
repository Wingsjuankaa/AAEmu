# Control de regresiones nativas AA10

Usar antes de modificar skills, buffs, plots, cooldowns, movimiento, packets o
primitivas compartidas.

Clasificar el cambio como:

- `client-native`: cliente/SQLite/captura AA10 prueba el contrato visible;
- `server-required`: AA10 prueba la mecánica y el servidor sólo aporta estado
  interno necesario;
- `upstream-integrated`: el padre exacto aporta el cambio y pasa gates locales;
- `diagnostic-only`: no altera gameplay ni wire;
- `custom-hypothesis`: compensación plausible sin evidencia suficiente.

Desplegar sólo las tres primeras clases. Mantener diagnóstico no mutante y no
fusionar `custom-hypothesis`.

Ante una regresión transversal:

1. Preservar captura, hashes, branch, imagen y estado sucio.
2. Comparar último bueno, upstream actual y candidato.
3. Probar igualdad de la clausura de datos antes de culpar código.
4. Distinguir “cliente no envió” de “servidor rechazó”.
5. Auditar ownership, orden, cooldown/GCD, parent-child plot edges, cleanup,
   observer broadcast y lethal boundary.
6. Eliminar compensaciones no probadas y restaurar el contrato mínimo.
7. Ejecutar prueba focal, consumidor no relacionado, suite completa y A/B real.

No añadir synthetic casts, replay server-owned, segunda autoridad de cooldown,
branches por skill/item ID, timings mágicos, packet suppression ni fallbacks
cero sin evidencia AA10 exacta.
