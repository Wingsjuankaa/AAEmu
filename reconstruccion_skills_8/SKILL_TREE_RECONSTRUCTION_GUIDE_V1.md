# Guia AA8 para reconstruir una rama completa de habilidades V1

## Alcance

Esta guia convierte el trabajo de Sorcery en un proceso repetible para las
demas ramas de ArcheAge Kakao 8.0.3.12 r558734. Cubre datos, codigo,
protocolo, persistencia, efectos temporales, plots, doodads, ancestral y
aceptacion viva.

La meta no es que una habilidad reproduzca una animacion. Una rama se cierra
cuando sus activas, pasivas y variantes ancestrales son aprendibles,
persistentes y funcionales de extremo a extremo, sin desconexiones ni efectos
fantasma.

## Reglas de autoridad

1. AA8 es la unica autoridad de implementacion y balance.
2. La compact activa es un runtime derivado, no la fuente de verdad.
3. Stage 20/30/50/60 y la consolidada AA8 se consultan antes de declarar una
   fila ausente.
4. Los dossiers de funciones y Stage 15 se consultan antes de volver al
   binario crudo.
5. El crosswalk AA8 -> 10.x r575 es obligatorio para reducir vacios. Puede
   confirmar identidad, continuidad y candidatos de relacion; no autoriza a
   importar balance, formulas, tiempos, IA ni protocolo 10.x.
6. Una relacion candidata 10.x solo se promueve si AA8 la confirma de forma
   independiente: resultado cacheado, consumidor, tooltip AA8, grafo cerrado
   o comportamiento vivo no ambiguo.
7. `rama_8_modern` es referencia de ideas, nunca destino ni autoridad.

## Definicion de cierre

Una rama esta cerrada cuando cumple simultaneamente:

- todas las activas visibles se aprenden al nivel correcto;
- las habilidades por defecto aparecen y no desaparecen al cambiar rama;
- todas las pasivas se asignan, remueven y recalculan en vivo;
- el cambio de especializacion refresca ventana, clase, niveles y banner;
- la seleccion persiste tras relog;
- cada activa aplica su costo, cooldown, animacion, objetivo, dano, control,
  buff, combo y ciclo de vida correctos;
- todas las variantes ancestrales se asignan, resetean, persisten y ejecutan;
- la progresion ancestral cruza cada umbral y conserva estado;
- cancelar por movimiento o interrupcion impide el efecto tardio;
- el cliente permanece conectado durante efectos inmediatos y periodicos;
- la suite automatica, integridad de compact y prueba viva quedan aprobadas.

## Fase 0: congelar el baseline

Antes de investigar:

1. registrar rama Git, estado sucio y archivos preexistentes;
2. registrar compact montada y su SHA-256;
3. registrar imagen Game, mounts, puertos y contador de reinicios;
4. etiquetar rollback de la imagen anterior;
5. capturar estado persistente de la especializacion del personaje;
6. no recrear Login ni MySQL durante iteraciones de skill;
7. usar un dummy controlado y, cuando una mecanica dependa de IA real, un mob
   normal como segunda superficie.

Cada version debe partir de un artefacto identificado. Nunca parchear una
SQLite anonima ni asumir que el contenedor usa el archivo recien construido.

## Fase 1: inventario funcional de la rama

Construir tres inventarios relacionados.

### Catalogo visible

Por cada activa y pasiva registrar:

- ID base y ranks;
- nivel de aprendizaje y puntos;
- icono, nombre y tooltip AA8;
- objetivo, rango, area, costo, casteo, canalizacion y cooldown;
- dano o curacion, control, buffs y combos declarados;
- skill por defecto y dependencias de aprendizaje.

### Catalogo ancestral

Por cada variante registrar:

- `heir_skill_id`, skill base, skill sucesora y active type;
- nivel ancestral requerido;
- item o transicion requerida, si existe;
- packet C2S de activar/resetear;
- packet G2C de lista y estado efectivo;
- skill visible frente a skills internas disparadas por plots o buffs.

### Matriz de aceptacion

Asignar a cada skill estados separados:

- `learn`;
- `persist`;
- `cast`;
- `visual`;
- `cost`;
- `cooldown`;
- `targeting`;
- `damage/heal`;
- `buff/control`;
- `combo`;
- `cancel`;
- `disconnect`;
- `relog`.

No resumir todo como funciona/no funciona. Sorcery demostro que una skill
puede tener animacion, MP y cooldown correctos y aun carecer de objetivo,
dano o cierre periodico.

## Fase 2: construir el grafo ejecutable AA8

La unidad de reconstruccion es la clausura, no la fila `skills`.

### Camino directo

`skill -> skill_effect -> effect -> actual effect`

El efecto concreto puede ser DamageEffect, HealEffect, BuffEffect,
SpecialEffect, KnockBackEffect u otro subtipo. Incluir condiciones, reagentes,
productos, projectiles, animaciones, tags y unit modifiers alcanzables.

### Camino por plot

`skill -> plot -> plot_events -> conditions/effects -> plot_next_events`

Registrar en cada evento:

- metodos de actualizacion de source y target;
- los once parametros opacos;
- tickets, delay, per-target, casting y channeling;
- area shape, relacion, flags y maximo de objetivos;
- skills, buffs, doodads o interacciones hijas.

### Camino por buff

`effect -> BuffEffect -> buff -> tick effects / triggers / unit modifiers`

Incluir eventos de inicio, fin, absorcion, daño, remocion y cooldown diferido.
Un buff visual sin `buff_tick_effects` o triggers puede ser una clausura
incompleta, no un bug de formula.

### Camino por doodad

`plot/special effect -> interaction -> doodad -> phase group -> phase funcs`

Seguir timers, finals, clouts, skill hits, ratios y transiciones. Para clouts:

`DoodadFuncClout -> aoe shape + inside buff + doodad_func_clout_effects`

El inside buff y los efectos por tick son canales distintos. Flame Barrier:
Mist tenia el slow en el primero y el dano en el segundo; por eso parecia
funcionar parcialmente.

### Roots tombstone

Una skill visible puede carecer de raiz en la compact aunque sus descendientes
existan. Restaurar la raiz exacta y su clausura, no reemplazarla por otra skill
con icono o descripcion parecidos.

## Fase 3: auditoria de materializacion

Comparar el grafo AA8 contra la compact activa tabla por tabla.

Clasificar cada ausencia:

- `root_missing`: falta la fila raiz;
- `edge_missing`: falta una relacion;
- `descendant_missing`: falta efecto, buff, forma o funcion alcanzable;
- `consumer_missing`: los datos estan, pero el servidor no los carga o usa;
- `protocol_missing`: el estado existe, pero el cliente no recibe el contrato;
- `scheduler_missing`: el cierre diferido se ejecuta fuera de orden o despues
  de cancelar;
- `wire_overflow/order`: los paquetes correctos salen con frontera, orden o
  volumen incompatibles;
- `semantic_parameter`: un parametro nativo se interpreta con unidad o
  significado incorrecto;
- `live_only`: los datos y consumidores cierran, pero la conducta real no.

Crear un constructor reproducible que copie el baseline e inserte solo filas
AA8 demostradas. Cada fila debe conservar locator, clasificacion, hash y
proyeccion de columnas. Si el esquema del runtime renombra columnas, declarar
el alias de forma explicita y probarlo.

## Fase 4: pase obligatorio por crosswalk 10.x

Para cada raiz, fila o relacion ausente:

1. consultar `logical_table_crosswalk`;
2. localizar `row_comparisons` y `relation_comparisons`;
3. registrar clasificacion y estado de evidencia;
4. usar coincidencias exactas para orientar la busqueda AA8;
5. poner en cuarentena conflictos y propiedades cambiadas;
6. nunca promover columnas de balance por identidad de ID.

Interpretacion practica:

- `exact_id_exact_relation`: fuerte corroboracion, pero AA8 sigue mandando;
- `stable_id_changed_properties`: identidad util, propiedades no promovibles;
- `renumbered_row_stable_relation`: usar la relacion natural y demostrar el
  nuevo ID AA8;
- `structural_candidate`: sirve para encontrar la frontera AA8 ausente;
- `conflict` o `blocked_cache_boundary`: detener promocion y escalar evidencia;
- `aa10_only`: no pertenece a AA8 salvo prueba independiente excepcional.

Flame Barrier ilustra el flujo correcto: r575 revelo `3792 -> 76542`, pero no
se uso hasta hallar la misma relacion en un resultado cacheado AA8 de 768
filas.

## Fase 5: escalamiento forense AA8

Orden recomendado:

1. SQLite de etapa y consolidada;
2. dossier de entidad/funcion;
3. indice semantico y dossiers reutilizables de Stage 15;
4. loader y consumidor de la tabla;
5. cached-result decoder existente;
6. busqueda de limite exacto en game0...game11;
7. x2game.dll, archeage.exe o game_pak crudos para un bloqueo demostrado.

Para un resultado cacheado nuevo:

- recuperar SQL y layout desde `query_specs`;
- localizar inicio, `SQLITE_ROW`, fin y `SQLITE_DONE`;
- validar cantidad, claves, unicidad y orden esperado;
- calcular SHA-256 canonico de filas;
- comparar la totalidad con el crosswalk, no solo la fila deseada;
- integrar el spec al decodificador comun;
- conservar offsets y consumidor en el manifiesto.

## Fase 6: reparar primitivas compartidas antes que hacks por skill

Si varias skills fallan con el mismo patron, buscar la primitiva comun.

### Targeting y areas

Validar:

- forma geometrica y unidades;
- centro usado: caster, target, previous target o punto sintetico;
- relacion friendly/hostile;
- flags de tipo y estado alive/dead;
- max targets y orden determinista;
- `hit_once` y memoria por evento;
- altura de terreno y tolerancia vertical;
- radio maximo frente a distribucion dentro del radio.

Gods' Whip Wave demostro que usar siempre el radio maximo produce animaciones
correctas con consultas vacias. `RandomArea` debe muestrear toda el area
nativa y preservar la Z segun su politica de terreno.

### Plots y cancelacion

Una interrupcion debe invalidar tareas ya programadas. Comprobar el estado de
cancelacion antes de cada evento diferido y antes de publicar efectos. El
defecto de Sorcery permitia cancelar el casteo por movimiento y aun ejecutar
la skill al terminar el timer.

### Buffs propios

Si todos los buffs sobre el caster se repiten en bucle, auditar eventos de
aplicar/remover, feedback C2S/G2C y reentrada. No arreglar cada buff por ID si
la causa es un eco transversal del mismo paquete o trigger.

### Daño periodico y transporte

Separar cuatro capas:

1. cambio autoritativo de HP;
2. IA y aggro del servidor;
3. `SCUnitDamagedPacket` visible;
4. `SCUnitAiAggroPacket` cliente.

Sorcery mostro que el daño podia ser correcto y aun desconectar por volumen u
orden de paquetes. Los ticks de un mismo instante deben compartir el lote
`CompressedGamePackets`; un aura multiobjetivo no debe crear una rafaga de
sobres fiables independientes. Mantener aislado el canal de aggro cliente si
su tabla exacta no esta reconstruida, sin desactivar el aggro autoritativo.

### Recursos de combate

No confundir MP, puntos de habilidad y recursos especiales. Recuperar opcodes,
layout y semantica exactos antes de emitir cambios. Una colision de opcode o
campo puede crear loops visuales en todas las skills que otorgan buff propio.

### Skills hijas y `SkillUse.value4`

Un SpecialEffect puede disparar una skill interna con semantica dependiente de
`value4`. Tratar ese campo como booleano generico rompe skills que necesitan
heredar target, posicion u owner. Documentar cada tipo de SpecialEffect y su
consumidor antes de generalizar.

## Fase 7: protocolo y estado efectivo

La representacion de skill seleccionada no basta. El cliente requiere:

- lista de ramas y niveles;
- puntos disponibles y asignados;
- lista de skills aprendidas;
- estado efectivo de variantes ancestrales;
- packets de cambio/reset;
- cooldowns y recursos;
- banner y nombre de la combinacion;
- refresh inmediato de ventanas relacionadas.

Al cambiar especializacion:

1. preservar el nivel historico de la rama entrante;
2. quitar activas y pasivas incompatibles de la rama saliente;
3. materializar la skill por defecto de la entrante;
4. recalcular puntos sin resetear ramas no cambiadas;
5. persistir antes de confirmar al cliente;
6. emitir el snapshot completo en orden determinista;
7. actualizar clase/banner y ventana Change Skillset;
8. validar por relog.

La progresion ancestral debe procesar XP excedente en bucle y emitir cada
transicion. Quedar en 100% significa que el servidor actualizo XP pero no
ejecuto o notifico el cambio de nivel.

## Fase 8: instrumentacion viva

Instrumentar por correlacion, no con mensajes sueltos. Cada uso debe poder
seguir:

- cuenta, personaje y sesion;
- skill visible e interna;
- plot, evento y ticket;
- source, target y punto sintetico;
- candidatos antes y despues de filtros;
- efecto concreto y cast action;
- daño calculado, HP anterior/nuevo;
- buff aplicado, tick, trigger y remocion;
- doodad, fase, clout y area trigger;
- lote de paquetes, cantidad y orden;
- cancelacion, excepcion, cierre TCP y reinicio del proceso.

Mantener un resumen automatico por ventana de prueba. La captura debe permitir
distinguir cero objetivos, cero efectos, daño interno sin packet y packet que
provoca desconexion.

## Fase 9: estrategia de pruebas

### Unitarias puras

Extraer helpers para semanticas con parametros opacos:

- conversion de unidades;
- resolucion de altura;
- muestreo de radio;
- orden de targets;
- filtros de tags;
- serializacion de packets;
- invalidacion por cancelacion.

### Integracion de datos

Abrir la compact construida y afirmar la cadena completa, no solo la raiz.
Ejemplo Flame Barrier:

`3792 -> 76542 -> 29874 -> 24585 -> 4167 -> 76543 -> 12209`

Validar `quick_check`, `integrity_check`, claves y ausencia de overwrites
silenciosos.

### Suite completa

Ejecutar siempre con Docker SDK 3.1.409 y la compact candidata montada en
`AAEMU8_SORCERY_RUNTIME` o la variable equivalente de la rama. El host moderno
sirve para iterar, no reemplaza la suite historica.

### Prueba viva

Para cada skill:

1. objetivo unico;
2. grupo AoE;
3. terreno plano e inclinado si usa posiciones;
4. casteo completo y cancelado;
5. primer uso, repeticion y cooldown;
6. objetivo con y sin combo/tag;
7. duracion completa de buffs/ticks;
8. relog y reuso;
9. mob real cuando el dummy no cubra IA, amenaza o movimiento.

## Fase 10: despliegue controlado

1. construir compact nueva, nunca editar la montada en caliente;
2. guardar manifiesto, SHA-256 e integridad;
3. ejecutar suite completa;
4. etiquetar imagen actual como rollback;
5. actualizar solo `COMPACT_DB` si corresponde;
6. construir Game con SDK 3.1;
7. recrear solo Game;
8. verificar mount real, imagen, puertos, logs y reinicios;
9. confirmar que Login y MySQL conservaron IDs y uptime;
10. documentar el comando de rollback.

## Fase 11: criterio de promocion

Una reparacion se promueve como:

- `automatic_verified`: datos, codigo y suites correctos;
- `live_accepted`: conducta observada y conexion estable;
- `quarantined`: evidencia parcial, sin despliegue;
- `rejected_hypothesis`: intento diagnostico refutado;
- `blocked_exact_boundary`: falta una frontera AA8 concreta.

No convertir una hipotesis desplegada en conocimiento. Sorcery V14-V20 fue
util para aislar aggro, pero solo V21 quedo aceptada: daño periodico agrupado y
aggro cliente intencionalmente cerrado.

## Patrones de fallo aprendidos en Sorcery

| Sintoma | Causa demostrada | Reparacion comun |
|---|---|---|
| No permite aprender | raiz/relacion tombstone ausente | restaurar raiz y clausura AA8 |
| Pasiva no asignable | catalogo/puntos/estado efectivo incompleto | materializar y sincronizar snapshot |
| Cambio visible solo tras relog | snapshot G2C incompleto o fuera de orden | emitir estado completo y banner |
| Rama entrante nivel 1 | se creo estado nuevo en vez de recuperar historial | preservar nivel por ability |
| Casteo cancelado igual impacta | evento diferido no consulta cancelacion | invalidar scheduler/plot |
| Buff propio entra en loop | eco transversal de recurso/buff | reparar protocolo/trigger comun |
| Animacion sin dano | target vacio o edge/descendiente ausente | trazar clausura y filtros |
| AoE visual lejos del suelo | p4 interpretado como offset Z | politica de terreno AA8 |
| Rayos correctos pero sin target | puntos solo en circunferencia | muestrear dentro del radio |
| Campo aplica slow sin dano | canal clout effect ausente | restaurar `clout -> effect` y ticks |
| Periodico desconecta tarde | paquetes por efecto fuera de lote | agrupar por tick |
| Daño funciona pero aggro desconecta | tabla cliente de aggro incompatible | separar aggro autoritativo/cliente |
| Ancestral queda en 100% | transicion no ejecutada/notificada | procesar umbral y enviar snapshot |

## Plantilla de dossier de reparacion

Cada cambio debe documentar:

- sintoma y reproduccion;
- skill visible e IDs internos;
- cadena AA8 completa;
- filas ausentes y por que faltaban;
- resultado del crosswalk;
- evidencia Stage 15/binaria usada;
- causa raiz en codigo o datos;
- cambio minimo y alcance transversal;
- pruebas focales y suite;
- compact, hashes, imagen y rollback;
- gate vivo y resultado;
- fronteras que siguen opacas.

## Aplicacion inmediata a Archery

Archery debe comenzar con esta secuencia:

1. generar catalogo base, pasivo y ancestral desde
   `archery-specialization-graph-v1.sqlite3`;
2. comparar su clausura con la compact V23;
3. producir matriz de roots/edges/descendants ausentes;
4. ejecutar crosswalk obligatorio para cada gap;
5. agrupar defectos por primitiva compartida ya reparada en Sorcery;
6. priorizar aprendizaje/persistencia, luego activas base, pasivas y ancestral;
7. reutilizar targeting, cancelacion, lotes periodicos, clout y estado ancestral
   ya cerrados;
8. abrir investigacion convencional solo para particularidades de Archery:
   projectiles, ammo, ranged weapon, auto-fire, movilidad, cargas o marcas;
9. construir compact Archery sobre V23 para no perder Sorcery;
10. exigir matriz viva y rollback propios antes de declarar la rama cerrada.

La guia es un proceso de evidencia, no una lista de IDs de Sorcery. Su valor es
que obliga a cerrar cada camino ejecutable y permite reconocer rapidamente si
un defecto nuevo es de datos, consumidor, protocolo, scheduler, transporte o
semantica espacial.

## Enmienda V1.1: hallazgos al aplicar la guia a Archery

La primera aplicacion completa revelo cuatro controles que pasan a ser
obligatorios para todas las ramas.

### Las pasivas son raices ejecutables independientes

El grafo de activas no sustituye `passive_buffs`. Auditar por separado:

`passive_buff -> buff -> tags/modifiers/triggers/ticks`

Archery tenia sus seis buffs concretos en la portadora, pero ninguna de las
seis filas `passive_buffs`; por eso una auditoria limitada a `skills` habria
declarado un falso cierre. El constructor debe comparar y materializar ambos
conjuntos de raices.

### Presentacion cliente no equivale a dependencia servidora

No todo ID llamado `anim` exige una fila en `anims` del servidor. En AA8:

- `SpecialEffect Anim (34)` puede participar en el tiempo del servidor cuando
  `plot_next_events.add_anim_cs_time=1`;
- `ProjectileAnim (38)` conserva una identidad de presentacion del cliente;
  sus valores pueden estar fuera del cache `anims` y el servidor no los busca;
- `Projectile (37)` si referencia una fila servidora de `projectiles`.

Antes de poner una skill en cuarentena, demostrar el consumidor exacto del ID.
Archery quedaba aislado por nueve `ProjectileAnim` inexistentes entre 1389 y
1439, aunque las quince relaciones observadas tenian `add_anim_cs_time=0`.
Separar esos IDs del conjunto requerido elimino el falso bloqueo sin inventar
filas ni importar presentacion 10.x.

### El estado de cuarentena tambien forma parte del runtime

Materializar filas no basta si `native_combat_skill_status` conserva la raiz
como `quarantined`: `SkillManager` la excluye antes de cargar. Un constructor
solo puede promover una rama cuando el grafo actualizado informa todas sus
raices como `enabled`; entonces debe sincronizar la tabla de estado y probar
que no queda ninguna raiz deshabilitada.

### Las primitivas de interfaz pueden cerrar mecánicas

`BubbleEffect` no aplica dano, pero si es una primitiva ejecutable: envia una
burbuja localizada por ID al objetivo. El backend vacio hacia que Concussive
Arrow: Mist quedara aislada aunque su canal de dano existiera. La reparacion
correcta fue implementar el paquete AA8 `SCChatBubble` y conservar el dano en
su camino de plot; no convertir `BubbleEffect` en un debuff inventado.

### Resultado del piloto Archery

La aplicacion de la guia produjo:

- 35/35 raices de skill habilitadas;
- 6/6 pasivas materializadas;
- 4.632 filas de clausura, 6 raices pasivas, relaciones owner-keyed, 356
  `tagged_skills` y 229 `tagged_buffs`, 5.022 filas AA8 materializadas en la
  capa V4;
- cuatro plots ancestrales recuperados: 2927, 2928, 2941 y 2942;
- cero filas runtime provenientes de AA10;
- la primera verificacion cerro 8/8 pruebas de artefacto y 533/533 pruebas
  del servidor; la matriz V4 pasa 16/16, el auditor ampliado 9/9 y la suite
  instrumentada 565/565 al cerrar tambien tags de buffs pasivos.

El walker semantico V3 se hizo parametrizable por `ABILITY_ID` y se reutilizo
para Archery mediante un perfil delgado, sin copiar el algoritmo de Sorcery.
La auditoria dirigida recorre 35/35 entrypoints, seis pasivas, Combo/SkillUse,
controllers, ticks y triggers; el pase complementario cierra las 356
relaciones de tag. Termina con cero filas ausentes, cero unknowns externos,
cero duplicados y cero blockers graficos u owner-keyed. Estas pruebas deben
preceder toda matriz viva de una nueva rama.

Este resultado confirma el proceso comun, pero la aceptacion viva sigue siendo
un gate separado: una rama no pasa de `automatic_verified` a `live_accepted`
hasta probar cada activa, pasiva y variante ancestral dentro del cliente.

## Enmienda V1.2: auditar el subtipo y su frontera de autoridad

Una fila `plot_effects.actual_type='SpecialEffect'` no queda cerrada solo
porque el backend generico exista. Cada `special_effect_type_id` alcanzable
es un contrato distinto y debe auditarse por separado:

1. resolver el nombre exacto desde el enum AA8 o desde evidencia binaria;
2. identificar sus campos en la plantilla y el valor transmitido por el plot;
3. localizar el consumidor real (servidor, cliente o ambos);
4. cargar todos los campos AA8 aunque el estado visible lo mantenga el cliente;
5. implementar solamente la parte que pertenece al servidor actual;
6. agregar una regresion que fije IDs, valores y campos de plantilla.

Archery expuso este hueco con `SpecialEffect 158`. El crosswalk 10.x redujo la
opacidad al nombrarlo `charge_cooldown`, y AA8 confirmo el mismo contrato en
sus propias filas y en el corpus Stage 15. Cuatro skills Archery usan cargas:
11368 (2/8000 ms), 13281 (5/22000 ms), 38893 (3/16000 ms) y 42851
(3/8000 ms). Los efectos 41872 y 55123 transportan 16000 y 22000 ms.

El cliente AA8 mantiene la lane visual y emite el cambio de conteo. En esta
arquitectura, el servidor registra cooldowns ordinarios pero no rechaza usos
desde ese cache. Por ello, la reparacion exacta carga `charge_count` y
`charge_cooldown_time` y reconoce el descriptor 158; no inventa un paquete o
un segundo arbitro de cooldown. Si en el futuro se hace autoritativo el
cooldown general, cargas debe integrarse en esa misma politica transversal.

Regla reusable: distinguir siempre entre **datos autoritativos**, **estado
presentado por el cliente** y **validacion que el servidor realmente ejerce**.
Un no-op silencioso pierde evidencia; una implementacion demasiado ambiciosa
puede crear una semantica que el cliente AA8 nunca tuvo.

## Enmienda V1.3: relaciones owner-keyed y requisitos heredados

Una clausura que solo recorre tablas con columna `id` puede declarar un falso
cierre. Antes de promover una rama hay que inventariar tambien tablas cuya
identidad es compuesta o depende del owner, por ejemplo:

- `unit_reqs (owner_type, owner_id, kind_id, value1...)`;
- tags y relaciones many-to-many;
- condiciones de aprendizaje o equipamiento;
- restricciones que viven en la skill base pero gobiernan sucesoras
  ancestrales.

Archery demostro el fallo con doce `unit_reqs` exactos de AA8. Once skills
exigen `equip_ranged` kind 29/value1 0, que en AA8 significa arco holdable 19;
la skill 10694 exige ausencia del buff tag 27 mediante kind 30. La SQLite ya
contenia las filas, pero el servidor nunca las cargaba ni evaluaba. El
crosswalk 10.x sirvio para resolver los nombres del enum; holdables, valores,
resultados y conducta se confirmaron en AA8 antes de implementar.

Proceso reusable para estos contratos:

1. auditar todas las tablas owner-keyed alcanzables por la rama;
2. resolver el enum y su consumidor antes de interpretar `value1..3`;
3. cargar solo kinds demostrados y dejar neutrales los opacos;
4. evaluar antes de mutar GCD, recursos o estado del casteo;
5. en AND, rechazar ante cualquier requisito demostrado que falle;
6. en OR, aceptar un requisito demostrado que pase, pero no rechazar si queda
   una rama opaca que podria autorizar;
7. si una sucesora ancestral no posee filas propias, buscar el requisito en su
   skill base mediante la relacion `heir_skill -> successor`;
8. emitir el `SkillResult` nativo en vez de reutilizar un error generico;
9. fijar en pruebas tanto la fila exacta como la semantica del evaluador.

Regla nueva de cierre: **roots, descendants y consumers no bastan; tambien
deben cerrarse las relaciones owner-keyed y su herencia entre skills visibles
e internas**. Esta auditoria debe ejecutarse antes de la matriz viva para que
una animacion funcional no oculte requisitos de arma, tags o estado ausentes.

## Enmienda V1.4: trazabilidad viva y criterio de cierre

Una animacion correcta no demuestra ejecucion servidor, y un numero de dano
en pantalla no demuestra por si solo que el HP autoritativo cambio. La
aceptacion de una rama requiere una traza que una el ciclo completo:

`request -> use_result -> plot_event -> DamageEffect -> HP before/after -> ended`

La instrumentacion compartida debe registrar, como minimo:

- arbol, skill visible o interna, `tlId`, caster y target;
- mundo e instancia;
- resultado, cancelacion, MP, cantidad de targets y efectos;
- `effect_id`, tipo de dano, dano calculado y absorbido;
- HP antes y despues de aplicar el efecto;
- si se emitio el paquete de dano al cliente.

En AA8 esta traza se materializa con los prefijos estables
`[AA8SorceryLive]`, `[AA8ArcheryLive]` y `[AA8SkillDamage]`. La instrumentacion
no modifica targeting, formulas, orden de eventos ni paquetes: observa el
contrato existente y permite distinguir cuatro fallos que visualmente se
parecen:

1. el plot no alcanzo el nodo de dano;
2. el nodo alcanzo cero objetivos;
3. el efecto calculo cero o fue absorbido;
4. el HP cambio, pero el cliente no recibio o no represento el paquete.

Protocolo reusable de aceptacion:

1. probar una sola interaccion y detenerse;
2. capturar la traza desde el inicio del casteo hasta `ended` o cancelacion;
3. exigir `targets > 0` donde corresponda y `hpAfter < hpBefore` para dano;
4. en efectos periodicos, observar el numero y separacion de ticks y comprobar
   que cesan al expirar o remover el estado;
5. revisar desconexion, excepcion y reinicio del proceso antes de avanzar;
6. repetir cancelacion por movimiento y relogueo cuando la skill mantenga
   estado;
7. registrar resultado y evidencia en la matriz de la rama.

Regla final: una rama queda `automatic_verified` al cerrar datos, consumidores
y pruebas; solo pasa a `live_accepted` cuando cada activa, pasiva y variante
ancestral relevante ha demostrado su resultado autoritativo en cliente. Un
fallo particular vuelve al flujo forense desde su primer eslabon divergente,
sin invalidar los contratos ya demostrados.

El resumidor reusable
`reconstruccion_skills_8/summarize_native_skill_live_trace_v1.py` transforma
los tres prefijos en ejecuciones JSON/CSV agrupadas por arbol, skill, `tlId` y
caster. El veredicto de dano exige simultaneamente `amount > 0` y
`hpAfter < hpBefore`; por diseno no puede promover evidencia puramente visual.

## Enmienda V1.5: cached results owner-keyed sin columna id

Archery demostro que `unit_reqs` existia completo en AA8 aunque las etapas
canonicas no lo hubieran decodificado. El loader nativo recuperado usa:

`SELECT owner_type, owner_id, display_msg, kind_id, value1, value2, value3 FROM unit_reqs WHERE enable='t'`

El resultado exacto se encuentra en `game11`:

- SHA-256 fuente
  `E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031`;
- inicio `0x828B2C`, fin `0x87EC3C`;
- layout `78 68 38 68 68 68 68`;
- 13.053 filas y siete cadenas cacheadas;
- primera referencia de string `0x110FA`.

La fila `PlotCondition/14753` es exactamente
`display=1, kind=26, value1=1, value2=30, value3=0`. AA10 solo ayudo a nombrar
kind 26 `target_health_less_than`; fila, valores y consumidor son AA8. Snipe:
Flame usa asi un limite estricto de HP objetivo menor que 30%.

Regla nueva: los constructores id-keyed deben tener un canal separado para
tablas de identidad compuesta. No fabricar una columna `id`; fijar owner,
claves naturales, offsets, hash del blob y politica determinista de reemplazo.

## Enmienda V1.6: casteos liberables y eventos de ciclo de vida

`casting_useable` no significa cancelacion. AA8 divide Concussive Arrow: Flame
y Snipe: Lightning en bandas inclusivas segun el porcentaje de carga al soltar:

- 4000 ms: 0-24, 25-49, 50-74, 75-99, 100;
- 5000 ms: 0-20, 21-40, 41-60, 61-80, 81-99, 100.

El servidor debe registrar inicio y duracion efectiva del edge, calcular el
porcentaje al recibir `CSStopCasting`, liberar inmediatamente el plot y evaluar
condition kind 18. Solo un cast no liberable se cancela. La traza
`[AA8SkillCastRelease]` fija el porcentaje que selecciono la rama.

Archery tambien demostro que cargar un `buff_trigger` no basta. Los eventos
kind 11 `Landing` y kind 13 `RemoveOnMove` deben emitirse antes de retirar el
buff para que su efecto hijo aun conserve owner, caster y skill. Esto gobierna
Concussive Arrow y Deadeye y pasa a ser una auditoria obligatoria para todas
las ramas.

Finalmente, SpecialEffect `CombatDice` debe materializar un unico resultado
por target en `Skill.HitTypes`; DamageEffect y condiciones kind 9 lo reutilizan.
Volver a tirar en cada consumidor produce ramas y dano contradictorios.

## Enmienda V1.7: cerrar relaciones consultadas en sentido inverso

Un walker dirigido puede terminar sin blockers y aun omitir una mecanica. Las
tablas de cache consultadas desde un consumidor externo no siempre tienen una
arista saliente desde la raiz. Archery lo demostro con `tagged_skills`: el
camino `passive -> buff 889 -> skill_modifier(tag 3750)` estaba presente, pero
el grafo no podia inferir por si solo las skills seleccionadas por ese tag.

La V2 contenia tags historicos parciales/duplicados y cero consumidores para
3750. La correccion V3 reemplazo las relaciones de las 35 entradas Archery por
356 filas AA8 exactas: 35/35 raices cubiertas, 356 pares naturales unicos y 24
consumidores de 3750. Las 356 filas clasifican
`exact_id_exact_relation` en el crosswalk; ninguna fila AA10 entro al runtime.

V4 encontro la misma frontera en sentido `buff -> tags`. El wrapper
`passive_buffs` identificaba seis `buff_id`, pero el constructor no traia sus
filas `buffs` ni todas sus relaciones `tagged_buffs`. El carrier conservaba
copias historicas y ocho pares naturales duplicados. La correccion materializa
las seis filas AA8 actuales, cierra 21 tags pasivos y 229 relaciones para los
49 buffs seleccionados, y reemplaza cada particion por `(buff_id, tag_id)`.

Pase reusable obligatorio para cada rama:

1. inventariar caches del servidor y sus claves naturales;
2. enumerar relaciones many-to-many aunque no aparezcan en el grafo dirigido;
3. cerrar desde todas las skills visibles, sucesoras, login-stage e internas,
   y desde todos los buffs referidos por pasivas/efectos;
4. reemplazar por clave natural, no por IDs historicos potencialmente
   duplicados;
5. exigir cobertura de raices, unicidad de pares y consumidor para todo
   modificador que seleccione por tag o skill;
6. incluir esas relaciones en manifiesto, hash canonico y crosswalk;
7. hacer fallar el auditor si un tag de modificador queda sin consumidores;
8. prohibir pares duplicados tanto en `(skill_id, tag_id)` como en
   `(buff_id, tag_id)`.

Tambien se fijo una frontera de autoridad nueva: antes de declarar obsoleto el
texto localizado hay que demostrar que el runtime contiene la fila AA8
actual. En Archery, la base forense AA8 ya tenia las descripciones actuales;
eran las copias historicas del carrier las obsoletas. Cuando tooltip, carrier
y evidencia nativa divergen, se reemplaza el carrier por la fila AA8 completa,
se conserva el modificador/relacion nativo y la prueba viva mide el consumidor;
no se fabrica balance desde la traduccion ni desde AA10.

Regla de cierre ampliada: **grafo ejecutable, filas de owner, relaciones
owner-keyed y caches de lookup inverso en ambos sentidos deben aprobar
auditorias independientes**.

Cuando la clausura termina en un consumidor hardcoded, una busqueda decimal
del ID en el corpus no basta. Hay que clasificar cada coincidencia como
inmediato semantico, direccion, offset o dato incidental. En Archery, el unico
hit Stage 15 para `7565` era `[RBX+0x1D8D]`: un offset de estructura, no el ID
del buff. Un falso positivo de este tipo se registra como evidencia negativa y
mantiene el gate vivo; nunca autoriza a implementar la descripcion o AA10 como
formula servidor.

### Ejecutar la suite contra el runtime compuesto exacto

La suite C# contiene pruebas de progresion ancestral que abren la compact
indicada por `AAEMU8_SORCERY_RUNTIME`. Dentro del contenedor Linux, omitir esa
variable activa un path Windows inexistente y produce dos falsos fallos
(`MaxLevel=0` y lista ancestral vacia). La invocacion reproducible debe montar
el directorio de runtimes y fijar explicitamente la compact candidata:

```powershell
docker run --rm `
  -e AAEMU8_SORCERY_RUNTIME=/runtime/compact-8.0-runtime-archery-v4.sqlite3 `
  -v 'D:\Proyectos\AAemu\rama_8:/src' `
  -v 'D:\Proyectos\AAemu\client_kakao:/runtime:ro' `
  -w /src mcr.microsoft.com/dotnet/sdk:3.1.409-focal `
  bash -lc 'dotnet restore AAEmu.Tests/AAEmu.Tests.csproj && dotnet test AAEmu.Tests/AAEmu.Tests.csproj --no-restore --verbosity minimal'
```

Regla reusable: el hash del runtime montado por la suite debe ser el mismo que
el del candidato y el mount de Game. Una suite verde contra una compact vieja
no promueve el runtime nuevo; una suite roja por path inexistente tampoco
demuestra una regresion mecanica.

## Enmienda V1.8: propagar autoridad por contenedores diferidos

Flame Barrier: Mist revelo una frontera que la clausura estatica no detectaba.
La fila `doodad_func_clouts/3792` tenia `use_origin_source=1`, pero el
emulador descartaba la skill al ejecutar:

`InteractionEffect -> SummonDoodad -> DoodadFuncClout -> AreaTrigger`

El resultado visible funcionaba parcialmente, pero los buffs se creaban con
`skill=0`, nivel de habilidad 1 y los ticks no podian atribuirse a la skill
interna `41478`. Cargar el booleano sin consumirlo era equivalente a omitir la
relacion.

Pase reusable para cualquier efecto diferido:

1. inventariar flags `use_original_source`, `use_origin_source` y equivalentes;
2. comprobar que la instancia de skill, no solo su ID o caster, atraviesa cada
   doodad, tarea, area, buff y trigger;
3. conservar `skillId`, `tlId`, ability level y mundo/instancia cuando el
   contrato AA8 lo requiere;
4. impedir propagacion cuando el flag es falso;
5. verificar el packet de buff y el DamageEffect final con la misma skill;
6. exigir limpieza del contenedor diferido y ausencia de ticks posteriores;
7. agregar una regresion para ambos valores del flag.

Regla de cierre ampliada: **una relacion diferida no esta cerrada hasta que su
contexto de origen llega al consumidor final**. La presencia de la fila y el
dano visual no bastan si el origen se pierde en una frontera asincrona.
