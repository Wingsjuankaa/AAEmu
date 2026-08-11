# Guia AA8 para reconstruir una rama completa de habilidades V1

## Alcance

Esta guia convierte el trabajo acumulado de Sorcery, Archery y Battlerage en
un proceso repetible para las demas ramas de ArcheAge Kakao 8.0.3.12 r558734. Cubre datos, codigo,
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

Archery demostro el fallo inicialmente con doce `unit_reqs` exactos de AA8.
Once filas exigen `equip_ranged` kind 29/value1 0 (arco holdable 19), mientras
la skill 10694 exige ausencia del buff tag 27 mediante kind 30. La primera
clausura era todavia incompleta: nueve alternativas OR para rifle/shotgun
holdable 31 existian en el mismo cached result AA8, pero su `owner_type` era
la referencia internada anterior `<ref:69872>` y el extractor no la resolvia.

El pase obligatorio r575 identifico el patron exacto `Skill + kind 29 +
value1 2`. AA8 lo confirmo de manera independiente mediante las nueve filas
de `game11`, `or_unit_reqs=true`, los campos `shot_gun_*` de las skills y el
holdable 31. V5 recupera las nueve relaciones desde AA8 y usa r575 solo para
resolver identidad/forma; cero filas 10.x entran al runtime. El resultado
correcto es arco **o** rifle para esas nueve skills, no una relajacion global
del requisito ranged.

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

Regla adicional para strings internados: un `<ref:N>` no es un valor opaco de
la fila, sino una dependencia de un cache anterior. Antes de descartar todas
las filas que lo usan, agruparlas por referencia, cruzar sus claves naturales
con el crosswalk clasificado y exigir corroboracion AA8 en owners y consumers.
Materializar solo el subconjunto cuyo tipo quede probado y registrar el conteo
recuperado; nunca sustituir el cached result con filas raw de otra version.

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

## Enmienda V1.9: distinguir instancias Multiple de un stack agregado

Deadeye (`skill 15073`) expuso un fallo visual que no era una fila de FX
ausente. Su cadena AA8 es estable hasta `buff 27704`, que declara
`stack_rule_id=4`, `max_stack=10` y `fx_group_id=1140`. El servidor creaba
varias instancias con indices distintos, pero serializaba todas con
`SCBuffCreated.stack=1`; al retirarlas, el cliente eliminaba el icono y el
bonus servidor, aunque dejaba vivo el FX compartido.

Para `BuffStackRule.Multiple`, no consolidar arbitrariamente las cargas en una
sola instancia: AA8 dispone de indice por instancia y de un campo `stack` en
el alta. Cada nueva instancia debe publicar su profundidad actual 1..N. El
paquete `SCBuffRemoved` sigue retirando por indice. Esta distincion debe
auditarse en cualquier skill que acumule un FX visible:

1. contar instancias activas del mismo `buff_id`;
2. verificar que los `SCBuffCreated` formen 1..N hasta `max_stack`;
3. registrar `owner/index` en cada `SCBuffRemoved`;
4. probar la salida completa sin relogueo, observando icono, stats y FX;
5. si solo queda el FX, revisar primero la semantica de stack y no reemplazar
   IDs AA8 por valores de otra revision.

El crosswalk r575 solo puede corroborar aqui: la skill, efectos y relaciones
de Deadeye conservan IDs/relaciones, y los campos estructurales del buff son
estables. No aporta una razon para cambiar duraciones, bonus ni balance AA8.

## Enmienda V1.10: no truncar `SCBuffRemoved` en AA8

La aceptacion viva de Deadeye falsifico el cierre inicial: los
`SCBuffCreated` formaron 1..N y todos los indices de `27704` recibieron su
retirada, pero el FX siguio visible. Esto obliga a inspeccionar el layout
completo del paquete antes de alterar FX, triggers o relaciones.

AA8 x2game.dll confirma en x64 `FUN_399ad0f0` y en x86 `FUN_39b83420` que
`SCBuffRemoved` contiene tres campos ordenados:

`unitId(BC) -> buffId/index(uint32) -> reason(byte)`

El tercer campo tiene default nativo `0`. Omitirlo produce un wire truncado;
que el cliente retire el icono no demuestra que haya consumido toda la
semantica de salida del buff. Desde ahora, toda reconstruccion de lifecycle
debe:

1. contrastar el paquete en las dos arquitecturas AA8 cuando existan;
2. probar bytes y longitud, no solo opcode y campos visibles;
3. registrar `owner/index/reason` durante la aceptacion;
4. mantener `reason=0` mientras no exista evidencia para otro valor;
5. no declarar cerrado un residuo visual hasta probarlo sin relogueo.

La correccion de Multiple sigue siendo valida: una reparacion necesaria puede
no ser suficiente. La prueba viva debe poder falsificar el diagnostico y el
checkpoint debe conservar ese resultado.

## Enmienda V1.10.1: correccion del contrato de `SCBuffRemoved 0x023`

La atribucion de V1.10 fue falsificada por la regresion viva de Charge. Las
funciones citadas alli (`FUN_399ad0f0` x64 y `FUN_39b83420` x86) serializan
otro tipo de paquete que sí tiene `unitId + buffId + reason`; compartir nombres
de campos no demuestra identidad de opcode.

La resolucion desde los factories específicos de `0x023` prueba el contrato
correcto:

- x64 `FUN_393362a0` usa la vtable `PTR_FUN_39cfa388` y el serializer
  `FUN_399ab070`;
- x86 `FUN_393266f0` usa `PTR_LAB_3a091ac0` y el serializer
  `FUN_39b81990`;
- ambos escriben exactamente dos campos: `objId(BC) + buffIndex(uint32)`;
- `SCBuffRemovedPacket` no lleva `reason` en AA8 r558734.

Regla transversal: una funcion reflectiva con campos plausibles no se puede
asignar a un paquete hasta enlazarla con el factory del opcode, su vtable y el
serializer invocado. Las pruebas deben fijar también la ausencia de bytes
finales ajenos al contrato.

## Enmienda V1.11: entradas de liberacion y muerte posterior a DD04

Las variantes de Concussive Arrow: Flame y Snipe: Lightning demostraron que
`casting_useable` no implica una segunda `CSStartSkill`. En AA8 r558734 la
tecla mantenida o repetida genera `0x159` con siete bytes:

`actorObjId(BC,3) -> mode(uint16) -> plotTlId(uint16)`

Un error de un solo byte al decodificar el campo central conserva el opcode en
el log pero desplaza el timeline, por lo que parece que el cliente nunca pidio
liberar. Para reconstruir una entrada desconocida se debe conservar el payload
crudo, comprobar bytes consumidos/restantes y usar una accion alternativa
conocida —en este caso saltar mediante `CSStopCasting`— como control positivo
del consumidor interno.

La primera aceptacion propuso diferir la muerte para publicar primero el dano
letal, pero el A/B historico la falsifico. La imagen Docker estable de las
20:19 no contiene la primitiva diferida; la imagen de las 20:38 ya contiene
`deferDeath`, `FinalizeDeferredDeath` y acciones post-envio, y coincide con el
inicio de las desconexiones al morir un NPC. La traza defectuosa mostraba
`SCUnitDamaged -> SCUnitPoints(0) -> SCUnitDeath` y el cliente dejaba de emitir
C2S al comenzar esa clausura.

El patron reusable corregido es:

1. preservar `ReduceCurrentHp -> OnKill -> DoDie` como una transicion
   sincronica;
2. permitir que `DoDie` cierre buffs, muerte, loot, aggro, target y EXP;
3. publicar `SCUnitPoints(HP=0, MP=0)` al volver de `DoDie`;
4. conservar `SCUnitDamaged` en su lote DD04 original, sin una cola lateral de
   mutaciones autoritativas;
5. validar cada cambio de orden contra una ejecucion historica conocida, no
   solo contra un oraculo headless creado durante la investigacion;
6. conservar de forma independiente los arreglos de layout, contador y
   limpieza que tengan evidencia AA8 propia.

## Enmienda V1.12 (falsificada): no equiparar estructuras internas y wire

Corregir el orden `SCUnitDamaged -> SCUnitDeath` no cerro por si solo la caida
al morir un NPC. Una prueba negativa —matar el mismo objetivo sin Fending—
confirmo que la skill era inocente y llevo al layout de `SCUnitDeath`.

La primera lectura asumió que el bloque interno AA8 r558734 implicaba este
cuerpo de red:

`victim BC + reason u8 + resurrection u32 + specialResurrection u32 + autoResurrection u32 + lostExp i32 + durability u8 + killer BC`

Si `killer != 0`, continua con:

`gameType u8 + killStreak u16 + param1 u8 + param2 u8 + type u32 + killerName string`

La implementación de esa hipótesis añadió un tercer tiempo `uint32` y cambió
`type` de `u8` a `u32`. La aceptación viva siguió fallando. Un A/B contra la
imagen Docker funcional de las 20:19 demostró que el servidor que sí permitía
matar NPC transmitía el cuerpo compacto original. `FUN_39AB5D30` es un
inicializador de estado interno de 17 bytes, no evidencia suficiente del
serializer wire.

Regla reusable: cada paquete con sentinel, unión o cola condicional necesita
pruebas byte a byte para todas sus ramas, pero los campos de una estructura de
estado no se promueven al wire sin localizar el serializer o una captura
compatible. Cuando una ejecución histórica funcional contradice una
interpretación estática indirecta, conservar ambas evidencias y probar el
cuerpo observado antes de ampliar el paquete.

## Enmienda V1.13: efectos tardios dentro de un plot letal

Un plot no termina necesariamente cuando uno de sus `DamageEffect` mata al
objetivo. Puede avanzar a efectos posteriores y tratar de crear un buff sobre
la misma unidad. Archery lo demostro con Blazing Arrow (`skill 15096`): tras
`SCUnitDeath`, el servidor publico el buff `2214`, aunque AA8 declara para esa
fila `dead_applicable=0` y `remove_on_death=1`.

Este fallo no se corrige cambiando el paquete de muerte ni truncando el plot.
La regla reutilizable es aplicar el contrato declarativo en el punto activo de
admision del efecto:

1. antes de ejecutar `BuffEffect.Apply`, comprobar el estado vital del target;
2. si es una `Unit` muerta, rechazar el buff salvo `DeadApplicable=true`;
3. conservar las rutas de carga, restauracion y pasivas fuera de esta barrera;
4. capturar la secuencia completa, porque el paquete invalido puede aparecer
   milisegundos despues de una muerte aparentemente correcta;
5. probar tanto el rechazo normal como un buff explicitamente aplicable a
   muertos antes de generalizar el cambio.

La ubicacion de la barrera importa. Ponerla globalmente en `Buffs.AddBuff`
confunde una unidad en inicializacion (`Hp=0` transitorio) con una unidad que
murio durante combate. La implementacion validada queda en `BuffEffect.Apply`
y su regresion dirigida forma parte de una suite completa de 585 pruebas.

## Enmienda V1.14: el target de presentacion puede ser una posicion

Hammer Toss/Ollo's Hammer (`18757`, plot `440`) demostro que el objetivo que
recibe el cliente para presentar una skill no siempre debe conservar la
identidad de la unidad que recibira el dano. El evento intermedio `28784`, con
`target_update_method_id=5` y un area de volumen cero, materializa un
`PlotObject` posicional (`ObjId=uint.MaxValue`) que copia transformacion y
region del target anterior. El evento `3480` consume esa posicion mediante
`ProjectileAnim 909` y produce el martillo correcto.

Dos aproximaciones plausibles quedaron falsificadas por la prueba viva:

1. conservar el NPC real a traves del target update mantiene dano y stun, pero
   el cliente no reproduce el projectile nativo;
2. emitir un `SCSkillFired` adicional usando el projectile directo `308`
   genera un FX parecido, adelantado y desincronizado con el gesto y el golpe.

Regla reusable para cualquier rama con una skill `plot_only`, FX ausente o
presentacion desincronizada:

1. reconstruir primero toda la cadena `plot event -> target update -> special
   effects -> ProjectileAnim/Anim/FxGroupAnim`;
2. registrar por separado el target de presentacion y el target autoritativo
   de dano; no exigir que tengan la misma identidad;
3. conservar un target posicional cuando lo declare el plot, aunque no exista
   como unidad registrable en el mundo;
4. no promover un projectile directo de la skill a paquete adicional si el
   plot ya es autoridad de presentacion;
5. comparar contra una ejecucion historica funcional antes de crear una ruta
   server-derived;
6. exigir en Mechanics Lab ausencia de fire duplicado, un solo dano y cierre
   completo del plot, pero reservar el veredicto de FX para el cliente real;
7. fijar una regresion para que el Lab considere visible la posicion sintetica
   sin convertirla en unidad real.

La evidencia completa, incluyendo el A/B V2/V3/V4, IDs, hashes, ledger y
aceptacion visual, vive en
`shared_primitives/CHECKPOINT_AA8_PLOT_ONLY_POSITIONAL_PRESENTATION_V1.md`.

## Enmienda V1.15: procedencia de buff no equivale a vínculo toggle

Charge `11918` reveló una regresión transversal de `SCBuffCreated 0x36C`. El
servidor empezó a escribir la skill origen en el campo compacto `s` de todos
los buffs. El cliente conserva ese campo como relación funcional y, al retirar
`7543` y `11344`, volvía a iniciar visualmente los 12 segundos base de Charge.

La regla reusable es separar procedencia de relación cliente:

1. conservar `Buff.Skill` como `originSkill` para mecánica y trazabilidad;
2. serializar `toggleSkill=originSkill.Id` sólo cuando
   `originSkill.ToggleBuffId != 0` y coincide exactamente con el buff creado;
3. serializar cero para buffs normales, procs, debuffs y buffs secundarios;
4. no rellenar IDs opcionales de packet sólo porque el servidor conoce su
   procedencia;
5. cuando un bug aparece al expirar un buff, auditar también el packet de
   creación: la retirada puede consumir una relación incorrecta almacenada
   segundos antes;
6. comparar contra una revisión histórica funcional antes de añadir resets,
   snapshots o refrescos de UI;
7. fijar regresiones para no-toggle, toggle propietario, toggle no coincidente
   y preservación del `stack` y del layout restante;
8. cerrar el lifecycle en cliente real esperando todas las expiraciones sin
   relog.

La evidencia completa, las hipótesis falsificadas, el A/B, los hashes y la
aceptación visual viven en
`shared_primitives/CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md`.

## Enmienda V1.16: cooldown como estado autoritativo, no refresco visual

Battlerage cerró una frontera que Sorcery y Archery aún no habían necesitado
resolver de extremo a extremo. Inicio, reducción, reset y snapshot son
operaciones distintas.

Checklist obligatorio para una rama nueva:

1. iniciar una sola vez por cast aceptado y deduplicar por `TlId/castToken`;
2. iniciar `plot_only` al aceptar el cast, nunca en `SCPlotEnded`;
3. reducir el tiempo restante, con clamp a cero y no-op sin cooldown;
4. seleccionar por skill y por los tres cooldown tags;
5. reservar el snapshot masivo para login/reconexión;
6. no usar reset para representar reducción;
7. fijar framing AA8 por factory/serializer, sin copiar el nivel Modern;
8. probar requests duplicados y expiraciones de buffs mientras la barra corre.

Behind Gale (`12→10→8→6 s`) y Charge son los casos de referencia. La evidencia
positiva/negativa y el wire `0x038/0x34D/0x098` están en
`shared_primitives/CHECKPOINT_AA8_COOLDOWN_AUTHORITY_V1.md`.

## Enmienda V1.17: componer tiempos por fase y exigir combat-sync real

Un delay de arista y la finalización de controller pueden representar la misma
fase. Sumarlos siempre ralentiza skills multigolpe. La composición validada es:

`animSync + projectileTravel + max(edgeDelay, controllerCompletionDelay)`

Además, `add_anim_cs_time` se resuelve por perfil exacto de modelo/esqueleto;
un fallback cero no es tolerancia, es daño adelantado. Para cada skill con
controller o multigolpe:

1. auditar `value3/value5` junto con el delay de la arista;
2. usar la misma animación/perfil en packet y catálogo combat-sync;
3. publicar el evento visual antes del daño;
4. medir primer/último impacto y contar resultados exactos;
5. no modificar GCD/guard para compensar un problema de plot.

Tiger Lightning y Precision Wave son las referencias en
`shared_primitives/CHECKPOINT_AA8_PLOT_TIMING_COMBAT_SYNC_V1.md`.

## Enmienda V1.18: el catálogo de pasivas no sustituye su contexto de evento

Archery probó que pasivas, tags y relaciones inversas deben estar presentes.
Battlerage probó que eso todavía no basta: el trigger necesita owner, source,
target y original source reales, además de condiciones positivas y negativas.

Una rama nueva debe auditar también:

- `source_agent_id/target_agent_id`;
- tags requeridos y excluidos por cada agente;
- `group_id/group_rank` para progresiones mutuamente excluyentes;
- diferencia entre `Multiple`, `Extend`, replace y avance de rango;
- `max_life_time` y tareas de expiración antiguas;
- refresh visual de una instancia extendida mediante `SCBuffUpdated`.

Bleeding y Frenzy congelan estos contratos en
`shared_primitives/CHECKPOINT_AA8_PASSIVE_BUFF_LIFECYCLE_V1.md`.

## Enmienda V1.19: cierre de rama basado en delta y regresión compuesta

Cada cierre nuevo debe declarar explícitamente qué heredó y qué descubrió. No
volver a presentar como novedad una primitiva ya cerrada por otra rama.

La plantilla de promoción es:

1. tabla `rama previa → contratos heredados`;
2. tabla `hallazgo nuevo → evidencia positiva → hipótesis falsificada →
   checkpoint reusable`;
3. matriz visible por familia;
4. suite compuesta exacta de ramas anteriores;
5. dos corridas deterministas de Mechanics Lab cuando aplique;
6. gate vivo separado del lifecycle servidor;
7. límites honestos de la etapa aceptada.

Battlerage V10 es el ejemplo de referencia:
`battlerage/CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md`.

Su lección negativa principal es transversal: una suite verde puede omitir una
carrera entre requests del cliente y callbacks de servidor. Las skills
`auto_fire` conservan una sola autoridad de cast; nunca introducir replay
servidor sin una prueba nativa que demuestre que el cliente dejó de emitir.

## Enmienda V1.20: ninguna función custom sin contrato AA8

El cierre compuesto Sorcery/Archery/Battlerage demostró que una abstracción
transversal plausible puede conservar tests verdes y, aun así, romper el estado
interno del cliente. Antes de modificar una primitiva compartida, clasificarla:

- `client-native`: contrato probado por datos, código, wire o cliente AA8;
- `server-required`: bookkeeping necesario para ejecutar ese contrato, sin
  crear otra autoridad observable;
- `diagnostic-only`: instrumentación incapaz de mutar gameplay o wire;
- `custom-hypothesis`: compensación plausible sin consumidor AA8 probado.

Sólo las dos primeras categorías son desplegables. Una `custom-hypothesis` no
se promueve por pasar Mechanics Lab o la suite .NET.

Cuando una reparación de rama rompe otra:

1. preservar captura, imagen, DLL, compact y hashes;
2. comparar el cierre lógico completo para descartar deriva de datos;
3. distinguir ausencia de request cliente de rechazo servidor;
4. auditar por separado GCD/type 41, cooldown/reset, buffs, resultado wire,
   orden DD04, actor de plot y dirección de aristas;
5. comparar la DLL exacta que produjo el control positivo, no un commit cercano;
6. restaurar el contrato mínimo probado y retirar guards, replay, allow-lists,
   timers y state machines falsificados;
7. ejecutar la suite compuesta y validar el lifecycle en cliente real.

Flamebolt es el control de referencia. La regresión no era falta de una máquina
Combo servidor: `SCPlotEvent.actor` se había calculado desde las aristas
salientes, adelantando el ciclo de casteo un nodo. El runtime bueno usaba la
arista padre `Casting/Channeling`; `casting_useable` viajaba por el opcode
independiente `0x159`. Restaurar esa relación exacta recuperó
`10752 -> 24894 -> 24895` sin acelerar Endless ni añadir lógica por ID.

El procedimiento durable se mantiene en la skill global:
`references/native-first-regression-control.md`.
