# Frontera Migration Scaling / Bless Uthstin

Estado: `confirmed_static`; consumidor principal implementado; aceptación
dinámica pendiente.

## Evidencia

- dossier y checkpoint:
  `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\migration-scaling-frontier`;
- SQLite completa: 45 filas `item_bless_uthstins`, todas enlazadas a
  `items.impl_id=35`;
- Lua exacto y seis páginas de guía: UI, feature `bless_uthstin`, preview y
  confirmación;
- Zone r575 `x2game-dev_dedicate.dll` SHA-256
  `8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`:
  serializers, constructores, stride 0x1c y item-task types 153..158;
- Ghidra existente:
  `E:\AAEmu-Research\tools\ghidra\ghidra_12.1.2_PUBLIC` con JDK
  `E:\AAEmu-Research\tools\jdk\jdk-21.0.11+10`.

## Hechos promovidos

- stats/wire base cero: STR, DEX, STA, INT, SPI;
- item 42822 normal +1/-1; item 42325 especial +3/-3;
- General Merchant no vende ambos items en la build exacta;
- C2G 0x1BF consume y G2C 0x2EC entrega preview;
- C2G 0x1C0 devuelve todos los campos y G2C 0x2ED publica cinco stats;
- `type` es item template id, no function id;
- cancelar mantiene el item consumido;
- suma máxima considera sólo deltas positivos.

## Gaps preservados

- hora/boundary comercial exacta del reset diario;
- mutación server de Init/reset, extensión máxima, expand/select/copy page;
- aceptación en cliente y persistencia después de relog.

No rellenar esos gaps desde AA8. El consumidor actual responde fracaso
explícito para operaciones secundarias.
