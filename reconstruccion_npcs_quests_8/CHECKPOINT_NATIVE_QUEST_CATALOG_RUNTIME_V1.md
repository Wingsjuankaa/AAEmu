# Checkpoint: catálogo transversal nativo de quests V1

Fecha: 2026-07-30
Rama: `client_version/8.0.3.12-kakao-r558734-port`
Autoridad: ArcheAge Kakao `8.0.3.12 r558734`

## Resultado

Se construyó una primera frontera transversal ejecutable para las misiones
AA8. No es una selección manual por ID: las `7.826` quests nativas se
clasifican con las mismas reglas de cierre y cada exclusión queda registrada
en SQLite y en el manifiesto.

El candidato estricto contiene:

```text
quests nativas inventariadas                 7.826
quests nativas genéricas habilitadas           555
excepciones ya validadas conservadas              6
quests activas en el candidato                  561
quests en cuarentena                          7.265
tipos de acto nativos                             85
tipos con loader + consumidor habilitados         15
```

Las seis excepciones conservadas son `330`, `2255`, `2256`, `2257`, `2258`
y `2532`. Sus filas se copian desde el runtime base porque ya contienen
reparaciones acotadas validadas con cliente real.

## Fuentes exactas

```text
runtime base:
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-npc-visual-v1.sqlite3
SHA-256 A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7

grafo forense:
E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
SHA-256 807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC

dossier raíz:
E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-330.json
SHA-256 C47AAF43F7BBA5F16D31CD30EBCB9B60A5103C07E13DE39D382DECFBBE82CD68
```

El dossier de `quest:330` está bloqueado y se usó como evidencia negativa:
no se promovieron automáticamente su `next_component` opaco ni los skills o
items cuya clausura global aún no está confirmada.

## Builder y catálogo de cuarentena

El builder reproducible es:

```text
reconstruccion_npcs_quests_8/build_native_quest_catalog_runtime.py
```

El runtime agrega:

```text
aaemu_native_quest_runtime_catalog
aaemu_native_quest_runtime_act_support
```

La primera tabla contiene una fila por cada quest nativa con estado
`native_safe`, `validated_override` o `quarantined`, además de los tipos de
acto y referencias a items, NPC y doodads. La segunda cruza los 85 tipos
nativos con clase C#, loader y consumidor confirmado.

Una quest genérica sólo entra cuando:

- tiene una forma de componentes que el servidor puede recorrer;
- todo acto posee clase, loader, detalle y consumidor;
- los items tienen cobertura AA8 `complete`;
- los NPC y doodads existen en el runtime AA8;
- los grupos de monstruos tienen miembros completos;
- no depende de skill, buff, spawner o AI sin clausura;
- no contiene enlaces `next_component` colgantes.

Los alias se aceptan únicamente en los 15 actos habilitados, donde el
consumidor usa además un target nativo concreto.

## Cambios del consumidor

El servidor ahora carga desde `quest_contexts`:

```text
min_level
max_level
race
```

`QuestAvailabilityGuard` aplica los límites de nivel y el bitmask de raza AA8
al aceptar una misión. `CharacterQuests.Load` omite de forma segura una misión
activa antigua si su template ya no existe, evitando una excepción durante el
login. También se corrigió el nombre de tipo de `QuestActSupplyCopper`, que
antes impedía detectar el cobre personalizado.

## Validación

```text
unittest del catálogo SQLite                 8/8
tests dirigidos .NET Core 3.1               47/47
suite completa .NET Core 3.1               282/282
PRAGMA quick_check                              ok
PRAGMA integrity_check                          ok
auditorías de huérfanos                          0
```

Se hicieron dos builds desde cero:

```text
compact-8.0-runtime-native-quest-catalog-v1.sqlite3
compact-8.0-runtime-native-quest-catalog-v1-verify.sqlite3

bytes      137.535.488
SHA-256    2B7529ABFAAD3348101DD7CF968E1BACFF4BA1FAA303868E0382772159CD7459
```

Los dos artefactos son idénticos byte por byte.

## Decisión de despliegue

El candidato V1 no se desplegó.

Es una frontera estricta, no un reemplazo todavía seguro del runtime general:
de las `6.628` quests de la base, comparte `532`, agrega `29` nativas y
retiraría `6.096`. Además, ninguna familia inicial completa cerró todos sus
items y tipos de acto. Cambiar `.env` en este punto reduciría de forma severa
la disponibilidad de misiones.

El runtime activo, LoginServer, MySQL y los NPC visuales no fueron alterados.

## Próximo cierre transversal

El orden de mayor impacto que entrega el propio catálogo es:

1. materializar items de quest todavía `phase_a_candidate` o ausentes;
2. implementar `QuestActConAcceptItem`;
3. implementar los objetivos `QuestActObjZoneKill`, `QuestActObjCraft`,
   `QuestActObjSphere` y `QuestActObjExpressFire`;
4. cerrar skills/buffs de componentes;
5. resolver doodads ausentes y después habilitar una familia inicial completa.

La promoción a runtime se hará cuando una familia inicial pase pruebas
automáticas, arranque del servicio y aceptación/avance/entrega con cliente
real sin retirar masivamente quests de la base.
