# Migration Scaling / Bless Uthstin AA10

## Disponibilidad

La sustitución aleatoria principal está implementada y aceptada dinámicamente
en `rama_10`, gated por `Feature.bless_uthstin` (176). Leer antes de modificar,
desplegar o repetir una aceptación:

- proyecto: `Docs/AA10BlessUthstinMigrationScalingReconstruction_es.md`;
- evidencia: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\migration-scaling-frontier`;
- checkpoint: `migration-scaling-frontier\CHECKPOINT.md`.
- capturas de aceptación:
  `Docs/evidence/migration-scaling-2026-08-19`.

Ghidra ya está disponible en
`E:\AAEmu-Research\tools\ghidra\ghidra_12.1.2_PUBLIC`, con JDK en
`E:\AAEmu-Research\tools\jdk\jdk-21.0.11+10`. Reutilizar esa instalación y los
proyectos bajo `forensics\ghidra`; no descargar otra copia.

## Contrato cerrado

- páginas: hasta 3, stride 0x1c, cinco stats i32 y dos contadores i32;
- stats/wire: 0=STR, 1=DEX, 2=STA, 3=INT, 4=SPI;
- normal 42822: +1/-1; especial 42325: +3/-3;
- Consume C2G 0x1BF -> preview G2C 0x2EC -> confirm C2G 0x1C0 -> apply G2C 0x2ED;
- el preview es autoritativo del servidor y la confirmación compara todos los campos;
- General Merchant no vende los items activos en los datos exactos r575; usar entrega GM para pruebas.

Reset, extensión máxima y páginas permanecen fuera de este primer cierre de
mutación. Sus packets responden fracaso explícito. No afirmar que están
reconstruidos ni inventar semántica desde AA8.

## Aceptación cerrada

El 2026-08-19 se aceptó en el cliente retail r575 con `Wingsjuanka`, owner 1, y
únicamente `351 / o_hirama_the_west_2`:

- 42822: preview y aplicación `STA +1 / SPI -1`, normal `1/1`;
- un 42325 cancelado: consumido sin mutación ni incremento especial;
- otro 42325 confirmado: `STR +3 / DEX -3`, especial `1`;
- estado final: `4/200`, deltas `STR 3, DEX -3, STA 1, INT 0, SPI -1`;
- relog completo: UI y MySQL conservaron página, deltas y contadores;
- logs: `1BF -> 2EC -> 1C0 -> 2ED`; login `2ED + 2EF`.

Usar el documento y las capturas anteriores como baseline para regresión. El
intento forjado está cubierto por tests unitarios del handler, pues no existe
una acción retail legítima para producirlo. Reset, Copy/Activate, expansión y
extensión continúan fuera del cierre.

Una nueva ejecución sigue requiriendo autorización explícita para
desplegar/reiniciar y para iniciar sólo la Zone resuelta desde la posición
actual del personaje. No reutilizar autorización de otra mecánica.
