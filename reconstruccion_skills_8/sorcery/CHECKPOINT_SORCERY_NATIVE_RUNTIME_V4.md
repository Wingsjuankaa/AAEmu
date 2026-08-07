# Checkpoint Sorcery AA8 native runtime v4

> Superado parcialmente por `CHECKPOINT_SORCERY_NATIVE_RUNTIME_V6.md`: las
> filas doodad que aquí se clasificaban como candidatos estructurales 10.x
> fueron recuperadas directamente del `game11` AA8. V4 se conserva como
> historial del cierre ejecutable.

Fecha: 2026-08-04 (America/Santiago)  
Cliente objetivo: ArcheAge Kakao 8.0.3.12 r558734  
Rama y runtime activos: `client_version/8.0.3.12-kakao-r558734-port`, `rama_8`

## Resultado

Sorcery quedó cerrada estáticamente para sus 42 raíces nativas (12 skills
visibles y sus auxiliares, cadenas y variantes ancestrales). La auditoría no
registra ningún descriptor ejecutable sin handler. Las seis pasivas ya habían
sido aceptadas en vivo; las activas quedan desplegadas y pendientes de la
última aceptación manual dentro del cliente.

Artefactos finales:

- runtime: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v4.sqlite3`;
- SHA-256 runtime: `5496A350F6A18D19547DFA53EB8E7E8E79E5BC6ED8880698EAAE6114A6743011`;
- manifiesto: `generated/sorcery-specialization-v4.manifest.json`;
- SHA-256 manifiesto: `FBC084C38AD47E3AF5EE0EA3A1C27750F5F8C2BDA1461992D0EA5E93E77F4987`;
- auditoría: `generated/sorcery-executable-semantics-audit-v2.json`;
- SHA-256 auditoría: `EF4EA74952C251B52DE773A68B9E239A5F36DC2B99B6EFA775064FC4E3C56109`;
- matriz: `generated/sorcery-executable-semantics-matrix-v2.csv`.
- SHA-256 matriz: `531BD353E92FA16D75DF88B9B69A72C76B068FA05C0BFC902CF14E66B41D6DBF`.
- aceptación runtime fuerte:
  `generated/sorcery-runtime-acceptance-v4.json`;
- SHA-256 aceptación JSON:
  `9C28ECAA8FDFDCE76F2F4856785F0430ABC5C2EA7A698959B670EEABFDE39098`;
- matriz de las 12 activas:
  `generated/sorcery-runtime-acceptance-v4.csv`;
- SHA-256 matriz de aceptación:
  `E273FABBDF07FD4E6D92701D6AC08D32A3D3B59B688F5C8DD7F59E1077EBCBD1`.

## Jerarquía de autoridad aplicada

1. SQLite/catálogo/relaciones extraídas del cliente AA8.
2. Corpus nativo AA8 y evidencia de ejecución del cliente.
3. Crosswalk AA8→AA10 para resolver identidad y reducir huecos.
4. `x2game-dev_dedicate.dll` r575 sólo para interpretar primitivas cuya
   identidad es estable o exacta en el crosswalk.
5. Código fuente público de CryEngine para interpretar `pe_explosion`.
6. AAEmu histórico sólo como implementación de transporte; nunca como
   autoridad de balance.

La SQLite 10.x no se usó para sustituir daño, balance, protocolo, tasas ni
fórmulas AA8. Sus filas de grupo/fase/función de doodad permanecen clasificadas
como candidatos estructurales, anclados a endpoints e identidades AA8.

## Matriz de las 12 activas visibles

| ID | Nombre inglés AA8 | Cierre reconstruido | Estado |
|---:|---|---|---|
| 10151 | Freezing Earth | raíz observada en vivo, plot 3096, AoE, buffs y cooldown | habilitada |
| 10153 | Insulating Lens | buff 95, absorción, ExtendCharge y cooldown final | habilitada |
| 10664 | Meteor Strike | daño, área, derribo/retroceso angular | habilitada |
| 10667 | Freezing Arrow | proyectil, daño, slow y combos | habilitada; disparo observado |
| 10670 | Arc Lightning | daño, Shock, propagación y aggro | habilitada |
| 10752 | Flamebolt | cadena 10752→24894→24895, Burning/Conflagration | habilitada; cadena observada |
| 11314 | Frigid Tracks | rastro/doodad, freeze y expiración | habilitada |
| 11939 | Searing Rain | plot multi-tick y ResetAoEDiminishing | promovida desde cuarentena |
| 11967 | Chain Lightning | rebotes, Shock y daño decreciente | habilitada |
| 12796 | Magic Circle | buff 19037 y Magic Source | habilitada; buff observado |
| 14774 | Flame Barrier | wall/area, daño periódico y slow | habilitada |
| 23593 | Gods' Whip | cadena 23593→23646…23649 y coste creciente | habilitada |

Las variantes ocultas `36477`, `36478` y `39674` también se promovieron. Las
cuatro skills `11939`, `36477`, `36478`, `39674` estaban bloqueadas únicamente
porque `ResetAoeDiminishingEffect` era no-op. El runtime anterior había borrado
además sus relaciones ejecutables. V4 restaura la clausura completa AA8 y no
se limita a cambiar su etiqueta de estado.

## Daño y aggro

Se materializaron los 14 descriptores AA8 ausentes:

`9679, 9680, 9843, 9860, 9875, 11361, 11689, 11690, 12133, 12134, 12135,
12136, 12137, 12937`.

La fórmula base sigue el orden nativo observado en `FUN_398cc980`: daño fijo,
daño de nivel, DPS/arma con tiempo efectivo, variación de arma y finalmente
multiplicadores del descriptor/global/equipo. Se implementaron además:

- multiplicador de altura, fórmula AA8 11;
- multiplicador de rango, fórmula AA8 12;
- disminución AoE por índice de objetivo, con piso en 0.5;
- fórmula de aggro por nivel efectivo de habilidad;
- valores neutros para columnas nativas nuevas cuando una fila legada del
  portador las conserva en `NULL`. Esto evita el fallo de arranque observado
  en `damage_effects.fixed_type` sin inventar propiedades de daño.

## KnockBack: semántica nueva recuperada

Los 471 descriptores AA8 tipo 13 comparten este contrato:

- `value1`: magnitud total en milímetros;
- `value2`: elevación en grados;
- `value3` y siguientes: cero para esta revisión.

La implementación histórica de AAEmu ignoraba `value2` y tomaba `value3` como
altura. Eso era incompatible con todo el corpus AA8. La reconstrucción usa:

```text
magnitud_m = value1 / 1000
horizontal = magnitud_m * cos(value2 grados)
vertical   = magnitud_m * sin(value2 grados)
dirección horizontal = desde el caster hacia afuera del target
```

Pruebas de control de Meteor Strike:

- `1400, 75°` → `(0.362 m horizontal, 1.352 m vertical)`;
- `400, -15°` → `(0.386 m horizontal, -0.104 m vertical)`.

El cliente nativo mueve a los personajes. El servidor no repite ese movimiento
para evitar doble desplazamiento. Para NPC se añadió reconciliación posicional,
respeto de `NonPushableByActor`/buff `NonPushable` y una breve exclusión del AI
mientras termina el desplazamiento.

## PhysicalExplosion: frontera CryEngine

RTTI y callbacks de `x2game-dev_dedicate.dll` prueban que KnockBack y
PhysicalExplosion son primitivas distintas:

- `X2::WZKnockBackUnitPacket`, callback `FUN_393635d0`;
- `X2::WZPhysicalExplosionPacket`, callback `FUN_39363e90`;
- vector de actor/physics: `FUN_39258bb0`;
- construcción `pe_explosion`: `FUN_39336830`;
- serializador del paquete: `FUN_3936dfd0`.

El paquete físico contiene source ObjId, skill caster, target, posición y tres
floats. La función nativa asigna:

```text
rmin = radius
rmax = radius
r = radius
impulsivePressureAtR = pressure
holeSize = hole_size
explDir = (0, 0, 1)
```

El código fuente de CryEngine confirma `kr = pressure * r²` y presión
`kr / max(rmin², distance²)`. Como AA fija `rmin == r`, la presión es constante
dentro de `radius` y cero fuera. `hole_size` controla el agujero en geometría
destructible; no crea una zona muerta interior. Para el descriptor Sorcery 190:

- radio: 5 metros;
- hole size: 1 metro;
- presión: 100.

Se descartaron dos aproximaciones incorrectas: dividir el radio por 1000 y
aplicar caída lineal desde `hole_size`. AAEmu no contiene el mundo físico de
CryEngine (geometría, masa y área de superficie); por eso el servidor conserva
la primitiva como física declarativa y deja el debris/actor physics al cliente,
mientras el daño se ejecuta por su `DamageEffect` separado.

Fuentes primarias de CryEngine:

- https://github.com/MergHQ/CRYENGINE/blob/master/Code/CryEngine/CryCommon/CryPhysics/physinterface.h
- https://github.com/MergHQ/CRYENGINE/blob/master/Code/CryEngine/CryPhysics/physicalworld.cpp

## Controladores e interacciones

Los controladores `11660` y `11661` son `LeapSkillController` con identidad y
relaciones exactas AA8→AA10. La RTTI nativa distingue también
`X2::LeapSkillController` de `X2::ImpulseSkillController`. El update nativo de
Leap se localizó en `FUN_39241890`; AAEmu implementa su proxy de movimiento y
materializa ahora ambas filas necesarias.

`InteractionEffect.SourceDirection` se respetaba en datos pero se ignoraba en
código. `SummonDoodad` copia ahora la orientación del caster cuando ese flag es
verdadero, conservando la posición del target de plot.

## Dos cierres de doodad distintos

La revisión exhaustiva descubrió que había dos familias que no debían
confundirse.

### Wave Gods' Whip

Las interacciones `7406/7407` invocan doodads `13407/13406`. Ambas identidades
y filas base están confirmadas en AA8. Su cierre estructural materializado es:

- grupos `38626…38630`;
- fases `49136, 49137, 49339, 49340, 49913`;
- timers `16372, 16373` (transiciones cada 1000 ms);
- finals `5304, 5305, 5320`;
- controladores `11660/11661`;
- PhysicalExplosion `190`.

### Magic Circle ancestral

Los doodads AA8 `14623/14666` son las variantes Quake/Flame. Su cierre es:

- grupos `43090/43245`;
- fases `55165/55330`;
- clouts `4116/4121`;
- buffs `25646/25647`;
- proyectiles `1126/1131`;
- áreas `16482/16501`.

La primera v4 sólo contenía esta segunda familia; la verificación de los
`doodad_id` de `InteractionEffect` permitió detectar y reparar la ausencia de
Wave Gods' Whip antes de la aceptación manual.

## Recursos, pasivas y primitivas compartidas

Se conservaron las reconstrucciones aceptadas previamente:

- Magic Source id 8, máximo 60, grupo de recurso 7;
- paquetes AA8 de resource point/transform/update-time. La aceptación en vivo
  posterior detectó que Point aún compartía incorrectamente `0x175` con
  `SCAbilitySwappedPacket`; la prueba nativa y corrección definitiva a `0x315`
  están en `CHECKPOINT_SORCERY_COMBAT_RESOURCE_PROTOCOL_V11.md`;
- ManaCost nativo;
- Combo, AutoAttack y CancelOngoingBuff;
- interrupción ordinaria, channel y plot en DisturbCasting;
- SkillUse preservando el target disparador;
- SpawnDoodad sobre target de tipo Location;
- ResetAoEDiminishing;
- seis pasivas Sorcery, ya aceptadas en vivo por el usuario.

## Gate de materialización raíz por raíz

La auditoría de handlers no bastaba para probar que la SQLite activa contenía
cada fila alcanzable. Esa diferencia permitió detectar anteriormente que Magic
Circle estaba completo mientras faltaba la familia distinta de Wave Gods'
Whip. Se añadió `validate_sorcery_runtime_v4.py` como gate independiente del
builder y de la auditoría semántica.

El validador actual demuestra:

- 2.272 filas alcanzables del catálogo Sorcery AA8 presentes y comparadas
  campo por campo contra el runtime, con cero divergencias;
- 2.373 filas runtime seleccionadas en 34 tablas, incluyendo las dos raíces
  que cruzan el límite de caché y los cierres de doodad;
- 2.514 referencias ejecutables comprobadas explícitamente, aunque SQLite no
  declare FKs para ellas;
- resolución completa de `skill_effect -> effect -> concrete effect`, plots,
  events, conditions, next-events, buffs, triggers, ticks, controllers,
  projectiles, AoE, interactions, doodads, fases y funciones;
- 306 descriptores `SpecialEffect` con enum conocido;
- 12/12 nombres ingleses exactos presentes en `localized_texts`;
- 40 raíces estáticas Sorcery más 2 raíces vivas con estado runtime
  `enabled`;
- seis contratos `passive_buff -> buff` resueltos y enlazados con la
  aceptación en vivo ya registrada;
- construcción determinista del reporte: dos ejecuciones consecutivas
  producen el mismo SHA-256.

### Conflictos comparativos 10.x preservados

El crosswalk contiene tres conflictos dentro del universo Sorcery, ninguno en
las 12 activas visibles:

- `buffs.94`: 10.x cambió `skill_controller_id`; alcanza la raíz oculta
  `37837`;
- `skills.43464`: 10.x cambió `category_id`, `desc` y
  `target_area_radius`;
- `skills.43465`: el mismo tipo de divergencia que `43464`.

El runtime conserva en los tres casos la fila AA8 exacta. Los conflictos se
mantienen como evidencia comparativa y no se resuelven eligiendo propiedades
10.x. Esto confirma que el crosswalk redujo huecos sin convertirse en fuente
de balance o comportamiento.

## Validación automática

- SQLite: `quick_check=ok`, `integrity_check=ok`;
- 42/42 raíces auditadas;
- 0 raíces bloqueadas por handler;
- 2.272/2.272 filas AA8 exactas en runtime;
- 2.514/2.514 referencias ejecutables resueltas;
- 306/306 tipos especiales reconocidos;
- 12/12 activas con nombre inglés, cierre materializado y estado habilitado;
- 6/6 pasivas con contrato runtime resuelto y aceptación en vivo;
- 410/410 pruebas C# aprobadas;
- 18/18 pruebas de primitivas especiales Sorcery aprobadas;
- 7/7 regresiones estructurales del runtime aprobadas;
- 4/4 regresiones de auditoría aprobadas;
- 4/4 regresiones del gate de aceptación runtime aprobadas;
- imagen Docker compilada sin errores;
- scripts dinámicos: 0 errores, 8 warnings históricos.

## Despliegue y rollback

- `.env` monta `compact-8.0-runtime-transversal-sorcery-v4.sqlite3` en
  `/app/Data/compact.sqlite3` como sólo lectura;
- imagen Game: `sha256:550a1f6aa32422470f47640ff77414c6545b52358642f25274e195fa0702d5ea`;
- rollback: `aaemu-game:rollback-pre-sorcery-v4-20260804`, imagen
  `sha256:8bbaacec710c1c5faab2356936d9d4f953bd5dfd6050e418ec7d24284f96a72d`;
- sólo Game se recreó; Login y MySQL no se reiniciaron.

## Gate manual final

El procedimiento reproducible está en
`SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V1.md`.

Probar en sesión limpia las 12 activas, primero sobre un NPC aislado y después
sobre varios objetivos. Para cada skill registrar:

1. aprendizaje y persistencia tras relog;
2. start/fire/end sin rechazo ni desconexión;
3. daño, buff/debuff, cooldown y consumo de mana/recurso;
4. AoE, rebotes, cadenas y número de ticks;
5. movimiento/derribo visual y posición final de NPC;
6. creación, orientación, cambio de fase y desaparición de doodads.

Casos de alto valor: Meteor Strike para el ángulo de KnockBack; Searing Rain
para la promoción desde cuarentena; Frigid Tracks/Flame Barrier para lifecycle
de doodad; Gods' Whip y su variante Wave para controladores, explosión física,
timers y finals; Magic Circle Quake/Flame para los clouts candidatos.

No se declara aceptación funcional completa hasta observar esos casos dentro
del cliente AA8. Esa última frontera es deliberada: la auditoría demuestra
cierre y ejecución del servidor, pero sólo el cliente puede confirmar animación,
física y UX nativas.
