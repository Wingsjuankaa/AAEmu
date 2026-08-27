# Checkpoint AA10 crafting — revisión histórica externa

## Frontera

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Baseline: `30afa2fc6abde1ec571489a5e33fa49fda6f2910`.
- Padre exacto: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- Cliente: ArcheAge Returns `10.0.2.13 r575`.
- Craft Orders continúa fuera de alcance y no existe fallback legacy.

## Método externo

La clasificación cruza full, compact retail y compact runtime con catálogos
ArcheAge Codex US/JP actualizados para la familia 10.0.2.9, notas oficiales
archivadas y wikis regionales. La fuente externa se conserva como
corroboración: no sustituye el contrato AA10 ni permite copiar IDs, fórmulas o
timings.

ArcheAge Codex declara además que separa las recetas filtradas como test/unused
en `Folio -> By category -> Unused`. Sobre las 2.643 recetas bloqueadas por la
ola 5 anterior, el cruce produjo:

| Clase externa | Cantidad |
|---|---:|
| `external_unused` en US y JP | 2.242 |
| activa en ambos catálogos | 24 |
| activa sólo en US | 7 |
| activa sólo en JP | 7 |
| ausente en ambos | 363 |

La unión activa de 38 IDs se refinó por contrato:

- 16 candidatos persistentes: 9267, 11234, 11355, 12149, 12150, 12151,
  12152, 12177, 12178, 12189, 12190, 12250, 12251, 12252, 12253 y 12254;
- 12 recetas de evento condicionadas: 10900, 10902, 11097, 11098, 11099,
  11100, 11103, 11121, 11122, 11125, 11316 y 12220;
- 6 contratos regionales JP/US divergentes: 7392, 7393, 7394, 7395, 7794 y
  7795;
- 1 conflicto regional/de versión: 8864;
- 3 reutilizaciones de ID: 6277, 6872 y 6915.

Fuentes principales:

- `https://archeagecodex.com/us/` y sus catálogos `recipes`/`unused`;
- `https://archeagecodex.com/jp/` y sus catálogos `recipes`/`unused`;
- `https://archeagecodex.com/us/recipe/9267/`;
- `https://wiki.archerage.to/na-en/db/crafts/9267`;
- notas oficiales archivadas de ArchePaper:
  `https://store.steampowered.com/news/posts/?appids=304030&enddate=1655915584&feed=steam_community_announcements`;
- quest de la biblioteca ArchePaper:
  `https://archeagecodex.com/us/quest/11006/`.

## Promoción cerrada de recetas sin materiales

Se promueven exactamente 14 contratos intencionalmente vacíos:

- Tax Certificate 9267: cero materiales, skill 34912, 300 labor, Construction
  230.000, Building Nameplate 2392, 3 s, coste 230 y producto 31891 x5;
- 13 ArchePaper: 12149, 12150, 12151, 12152, 12177, 12178, 12189, 12190,
  12250, 12251, 12252, 12253 y 12254; skill 48802, 0 labor, Bookshelf 17370,
  1 s, coste 0 y un producto exacto cada una.

El recuerdo del operador de que Tax Certificate no consumía materiales coincide
con full AA10 y las fuentes externas. El campo `cost=230` se conserva: la wiki
lo representa como 2 plata 30 cobre, por lo que no se convierte en cero por
memoria ni inferencia.

La policy v5 ahora incluye `materialFreeCraftIds`. El loader exige que esos IDs
sean ejecutables, estén habilitados, tengan cero materiales y al menos un
producto. `CraftTransactionPlanner` y `ItemContainer` sólo aceptan un plan vacío
cuando porta esa marca; cualquier otra receta sin materiales continúa cerrada.

Resultado regenerado:

- 9.949 habilitadas;
- 7.320 ejecutables;
- 2.629 bloqueadas;
- `missing_materials`: 688;
- manifest SHA-256:
  `E0855AC4D9B39203FFE705E6A170EEA103EF129D3F311D04900103488469AC63`;
- policy SHA-256:
  `193BD16E9B9AAEAD102BA2188A3A53D4FBB6D0F0FDDFDA122A018F4F95190569`.

## Fronteras persistentes no promovidas

### Garden Crystal 11234

El contrato de full, retail y runtime coincide: tres materiales, producto 48513,
Archeum Workbench 566, dos membresías de craft pack y consumer nativo. Sin
embargo, `crafts.skill_id` es NULL en las tres fuentes. El servidor no puede
inventar la skill, labor ni lifecycle; queda bloqueada por `missing_skill` hasta
cerrar el consumer que ejecuta una receta sin skill explícita o demostrar un
skill fuera de `crafts`.

### Hardwood Raft 11355

Full, retail y runtime coinciden en skill 28009, material 49482 x1, producto
49474 x1, workbench 15386 y 3 s. Ninguna tabla con `craft_id` aporta
`craft_pack_crafts`, `item_recipes`, `items.craft_id`, Folio o un
`DoodadFuncCraftStart` vivo. Queda bloqueada por `missing_native_consumer` hasta
resolver su world/quest/event consumer; la página externa no basta para abrirla.

## Gates estáticos

- auditorías Python: 29/29;
- `dotnet restore`: correcto, sólo advisories ya conocidos;
- build Release: correcto, 0 errores;
- suite TUnit: 1.567/1.567, 0 fallos;
- full, compact retail y compact runtime: `quick_check=ok` e
  `integrity_check=ok` registrados por el manifest.

## Despliegue y gate dinámico

- imagen previa conservada como
  `aaemu-world:rollback-pre-crafting-material-free-20260827`;
- imagen desplegada:
  `sha256:e5b9c97b6e6c0efe78bf10356664df586a46608d05b9f7266c8fe13a2c5a277d`;
- Game inició sano y registró `12402 crafts (9949 enabled, 7320 promoted by
  AA10 crafting policy)`;
- se inició exclusivamente `o_the_great_reeds`, `zoneKey 288`, mediante el
  inspector tipado del mapa; World recibió el spawner retail, cargó 738
  unidades estables y mantuvo heartbeat fresco;
- tras la verificación se detuvo esa zona y el entorno quedó en Core sano,
  cliente detenido y `0/67` ZoneHosts activos.

El botón genérico del Control Center lanzó el cliente con las credenciales de
perfil `test/testtoken`, que Login rechazó. El Simple Launcher conserva el
usuario `codexwave4`, pero por diseño no guarda su contraseña. No se adivinó ni
se modificó la credencial, y tampoco se escribió directamente en MySQL. Por
ello el gate retail de 9267/ArchePaper queda **pendiente de autenticación**, no
fallido por crafting.

Cuando exista una sesión válida, la aceptación retail debe comprobar una receta
9267 y una ArchePaper: rechazo pre-cast por labor/actability/bolsa, un solo
commit, coste exacto, producto, repetición y persistencia tras relog.
