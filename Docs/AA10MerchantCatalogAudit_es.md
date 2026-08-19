# Auditoría AA10 — catálogos de vendedores

Fecha: 2026-08-19
Cliente objetivo: ArcheAge Returns 10.0.2.13 r575

## Problema probado

AAEmu cargaba exclusivamente `merchant_goods.enable = true`. El catálogo retail contiene 130
filas deshabilitadas; no pueden habilitarse en bloque porque mezclan contenido vigente, stock
retirado, eventos terminados y tiendas de prueba.

Dos contradicciones visibles quedaron confirmadas contra la SQLite completa y el compact retail:

- General Merchant, pack 145: la infusión 54335 afirma en su propia descripción que se compra en
  este vendedor, tiene precio 130 y una fila de catálogo válida, pero esa fila está deshabilitada.
- Weapon Merchant inicial, packs 119 y 120: los cofres 47868, 47869, 51185 y 53424 tienen precios
  válidos y selectores completos, pero sus ocho relaciones de catálogo están deshabilitadas.

Los cuatro cofres cubren una mano, dos manos, armas a distancia e instrumentos. Sus selectores
entregan 18 resultados válidos: 8 + 6 + 2 armas y 2 instrumentos. Los doce cofres Explorer de
armadura del pack 219 ya están habilitados y no requieren corrección.

## Cierre dual reconstruido

`Configurations/MerchantCatalog.json` contiene una allowlist exacta por `merchantPackId + itemId`.
El loader sigue descartando cualquier otra fila con `enable = false`. Cada relación configurada:

1. debe existir exactamente en la SQLite retail;
2. conserva grade, moneda, precio, tipo y límite del catálogo;
3. se valida contra el mismo pipeline de compra que el resto del vendedor;
4. se aplica a todos los NPC que usen el pack compartido;
5. emite evidencia de activación al arrancar y alerta si la relación desaparece.

La primera prueba dinámica reveló una segunda puerta: el cliente no recibe el catálogo completo
desde World, sino que construye las páginas con `merchant_goods.enable` de
`game/db/compact.sqlite3` dentro de `game_pak`. El servidor cargó y validó las 38 mercancías del
pack 119, pero el cliente mostró sólo las 34 habilitadas localmente. Las cuatro ausentes eran
exactamente 47868, 47869, 51185 y 53424.

`Scripts/PatchAa10MerchantCatalog.py` cierra esa proyección cliente sin ampliar la allowlist:

1. valida la identidad completa de las nueve filas r575;
2. acepta únicamente los estados booleanos `f` o `t`;
3. cambia sólo `enable: f -> t` en esas nueve filas;
4. compara todas las demás filas de `merchant_goods` antes y después;
5. ejecuta `PRAGMA quick_check`, conserva el tamaño exacto y es idempotente;
6. deja el modo dry-run como comportamiento predeterminado.

La SQLite completa de evidencia y la copia forense retail permanecen inalteradas. Sólo se corrige
la copia operacional del cliente y se reinserta la misma entrada en `game_pak` con
`Tools/PakEntryReplace`, que exige hash previo, tamaño idéntico y verificación posterior.

## Alcance inicial

| Pack | Vendedor | Ítems restaurados |
|---:|---|---|
| 119 | Weapon Merchant, niveles 1–10 | 47868, 47869, 51185, 53424 |
| 120 | Weapon Merchant, niveles 11–20 | 47868, 47869, 51185, 53424 |
| 145 | General Merchant | 54335 |

En los datos r575 estos packs están relacionados con 37, 26 y 382 templates de NPC,
respectivamente. La corrección se hereda por catálogo y no requiere mantener una lista de 445 NPC.

Las 121 relaciones deshabilitadas restantes conservan su estado retail hasta que exista evidencia
positiva individual. Entre ellas hay stock histórico de Honor/Vocation, eventos cerrados y goods
con monedas especiales; el nombre `Live` del pack no basta para promoverlas.

## Despliegue y rollback cliente

- Compact y entrada embebida antes: `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86`.
- Compact y entrada embebida después: `4B2771E24BE56CD3B2223F7EF5EE1B0C0D8A5002A95227E38B0A33EEEB96839D`.
- Tamaño lógico antes y después: `440823808` bytes.
- Tamaño de `game_pak` antes y después: `68963258880` bytes.
- SHA-256 completo de `game_pak` después: `06CBCD0E27225CC7EF617BFAF13D9D87A5059D15F3FF94C7941E41B2505BEB70`.
- Rollback: `E:\AAEmu\rama_10\backups\merchant-catalog-20260819-1720\compact.sqlite3`.
- Imagen World desplegada: `sha256:5533ef64bd4c...`.

Una segunda ejecución de `PakEntryReplace` respondió `Already patched`; el dry-run posterior
encontró `0` filas pendientes.

## Aceptación dentro del cliente

La aceptación se ejecutó con `Wingsjuanka` en `o_hirama_the_west_2` (zone key 351), levantando
únicamente esa Zone. Login, DB y World se mantuvieron saludables.

### Weapon Merchant, template 1176 / pack 119

- Antes del parche cliente: 4 páginas, 34 mercancías; ninguno de los cuatro cofres Explorer.
- Después: los cuatro cofres aparecen al inicio de la página 1 y se conservan las 4 páginas.
- Compra: `Explorer's 1H Weapon Crate` (item 47868) por 2 silver 50 copper.
- Uso: abrió el selector `Uncloak` con dagger, sword, katana, axe, club y el resto de opciones 1H.
- Resultado elegido: el cofre fue consumido y se adquirió `Explorer's Dagger` (item 47776).

### General Merchant, template 858 / pack 145

- `Story Quest Infusion` aparece en la página 1 junto a los scrolls de awakening.
- Compra: una unidad por 1 silver 30 copper.
- Resultado: la compra fue aceptada por World y el item 54335 llegó a la mochila.

Los NPC 1176 y 858 usados para la prueba fueron spawns transitorios y se retiraron después de la
aceptación. El cliente quedó abierto y la Zone 351 continuó activa.
