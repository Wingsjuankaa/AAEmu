# Checkpoint AA8 — admisión de Combo durante GCD

Fecha: 2026-08-09  
Autoridad: Kakao `8.0.3.12 r558734`, Stage 15 y compact AA8 activa

## Regla reusable

`SpecialEffect type 48 (Combo)` no ordena al servidor lanzar otra habilidad.
Describe la skill que el cliente pedirá a continuación y el tiempo durante el
cual esa petición pertenece a la misma cadena.

Cuando el primer intento de una continuación Combo aparece como
`CooldownTime` y el reintento unos cientos de milisegundos después funciona,
no se debe acelerar la animación, reducir el GCD global ni codificar una lista
de skills. El diagnóstico obligatorio es:

1. confirmar en `skill_effects → effects → special_effects` la relación type
   48 de la skill activa;
2. comparar timestamp del request siguiente con `value2` (ventana Combo), el
   guard fijo de requests y el GCD vigente;
3. admitir sólo `value1` como continuación dentro de esa ventana;
4. consumir la transición al elegirla y reemplazarla al aceptar otra skill;
5. dejar que la transición exacta omita sólo el GCD, conservando el guard de
   requests, cooldown propio, requisitos, rango y recursos;
6. no promover requests especulativos tempranos como cadencia de combate.

El catálogo AA8 estudiado contiene 83 descriptores efectivos, todos con
`chance=100`; existen fuentes con alternativas, condiciones de nivel y tags de
buff. Por eso el runtime consume los metadatos cargados y no una tabla manual
por especialización.

## Caso de aprendizaje

- Triple Slash: Lightning: `36401 → 36402 → 36403`, ventana 1000 ms;
- Whirlwind Slash: `13282 → 32040 → 32049`, ventana 1500 ms;
- requests nativos observados entre 217 y 335 ms;
- cada primer intento era rechazado por GCD y el retry añadía unos 500 ms;
- tras la corrección inicial: Lightning completa admisión en 500 ms y
  Whirlwind en 635 ms.

## Enmienda live: Endless Arrows y cadencia excesiva

Endless Arrows mostró requests de continuación anteriores a 150 ms. La
primera interpretación fue permitir que una transición Combo omitiera también
el guard. La aceptación visual posterior falsificó esa solución: el servidor
comenzó a aceptar impactos separados por sólo 47–103 ms, muy por debajo de su
`custom_gcd=220`, y aceleró igualmente otras cadenas Combo.

La cadena AA8 declara un descriptor type 48 en cada tramo:

- `14835 -> 14836`, ventana 1000 ms;
- `14836 -> 14837`, ventana 1000 ms;
- `14837 -> 14836`, ventana 1000 ms.

Los requests a 50–148 ms prueban que el cliente puede anticipar/repetir una
solicitud; no prueban que ésa sea la velocidad de impacto. El comportamiento
seguro restaurado para la comparación visual es:

1. aplicar primero el guard histórico de 150 ms;
2. después comprobar y consumir la transición Combo exacta y vigente;
3. permitirle omitir sólo el GCD;
4. continuar validando cooldown propio, requisitos, rango y recursos.

El guard de 150 ms es una protección histórica de AAEmu introducida en
`c7d201bf` (2020), no un timing probado de AA8. Se conserva temporalmente como
baseline solicitada; reemplazarlo por cadencia nativa por skill y coalescing
de requests tempranos es una reconstrucción posterior separada.

## Cadencia repetible: V8 falsificada y contrato V9

La prueba visual confirmó que la baseline evitaba la aceleración de Battlerage,
pero introducía pausas en Endless. V8 intentó reservar en el servidor el primer
request temprano hasta `custom_gcd`; la prueba viva falsificó ese diseño. El
cliente siguió emitiendo `StartSkill` y los callbacks diferidos compitieron con
él, alternando autoridades y TlId (`3844→3847`, `3871→3887`). Una suite
determinista verde no modelaba esa carrera de red.

Los datos AA8 que separan los contratos siguen siendo:

| Cadena | `auto_fire` | `effect_repeat_tick` | `custom_gcd` |
|---|---:|---:|---:|
| Endless base `14835/14836/14837` | 1 | 100 | 220 ms |
| Endless Flame `39663/39664/39665` | 1 | 100 | 700 ms |
| Endless Stone `39666/39667/39668` | 1 | 100 | 700 ms |
| Triple Slash / Whirlwind | 1 | 0 | propio de cada tramo |

El contrato corregido conserva una sola autoridad de cast, el cliente:

1. Combo ordinario conserva el guard de 150 ms y bypass sólo del GCD para el
   siguiente ID exacto;
2. el servidor nunca difiere, fusiona ni vuelve a ejecutar un request;
3. si un Combo repetible exacto (`auto_fire`, `effect_repeat_tick > 0`) llega
   antes del guard y no existe cooldown propio, se devuelve el rechazo nativo
   `CooldownTime`; el loop `auto_fire` del cliente decide el siguiente intento;
4. si existe cooldown propio, la respuesta continúa suprimida para evitar el
   reinicio visual de Charge y cualquier otra skill con timer autoritativo;
5. una transición expirada/no relacionada y las cadenas con
   `effect_repeat_tick=0` no reciben la excepción.

No hay allow-list de IDs. `auto_fire` se carga en `SkillTemplate` únicamente
como clasificación de feedback; nunca autoriza al servidor a crear un cast.
Éste es el antecedente obligatorio para futuras ramas: no introducir timers o
replays de servidor para loops cuya fuente autoritativa sigue siendo el cliente.

Evidencia completa y fixture live:
`../battlerage/BATTLERAGE_COMBO_CADENCE_V6_AA8.md`.

Gate live V9 aceptado: Endless Arrows quedó fluido, los TlId exitosos avanzan
de forma monotónica y cada solicitud anticipada observada fue contestada como
`clientOwnedRepeat=True`; no existe ningún callback o cast generado por el
servidor. Este contrato queda promovido para reparaciones posteriores.

## Regresión cruzada: no resetear tags Combo sin cooldown

La validación posterior de Sorcery probó que la continuidad cliente no depende
sólo de la admisión y del feedback `CooldownTime`. `SCSkillCooldownReset 0x098`
también puede destruir la transición local si se publica sobre el tag de una
cadena sin que exista un cooldown real.

Caso de referencia:

- Flamebolt base: `10752 -> 24894 -> 24895`;
- tag del root: `3308`;
- cooldown de las tres etapas: cero;
- con `IgnoreSkillCooldowns`, un reset espurio al terminar `10752` hacía que el
  cliente volviera a pedir el root y nunca alcanzara los hijos instantáneos.

Por tanto, una reparación de Combo debe verificar conjuntamente admisión,
feedback y resets publicados al finalizar. El modo GM no autoriza a fabricar
un delta: si `UnitCooldowns.ResetCooldown(selector)` devuelve no-op, no se
envía `0x098` ni se expande automáticamente de skill a tag.

## Regresión cruzada: el orden interno del nodo también es estado cliente

El segundo incidente de Flamebolt del 2026-08-10 descartó nuevamente datos y
admisión: los cierres exactos de `10752/24894/24895` eran idénticos entre la
compact Sorcery V10 conocida como buena y Battlerage V5. La captura
`aa8-game-20260810-230807748-session-3672589487.jsonl` mostró sólo tres
requests `10752`, cero `24894/24895` y cero paquetes reset `0x098`.

El contraste Git `835b42e1..73243c9e` aisló otra mutación cliente-visible:
`PlotNode` pasó de publicar los efectos del nodo y luego `SCPlotEvent` a
insertar siempre `SCPlotEvent` delante de todos sus resultados dentro del
mismo DD04. Esa inversión nació para combat-sync de Battlerage, pero se aplicó
también a cadenas `auto_fire` cuyo siguiente ID lo selecciona el cliente.

La compatibilidad se clasifica sólo con datos AA8:

- `auto_fire=1`;
- al menos un `SkillEffect -> SpecialEffect type 48 (Combo)`;
- plot ejecutado por el servidor, transición siguiente ejecutada por el cliente.

Para ese contrato se conserva el orden probado anterior del nodo. No existe
allow-list de skills. Los plots ordinarios mantienen el batch visual nuevo;
Endless Arrows no cambia de autoridad ni recibe replay servidor. El fixture
`sorcery_flamebolt_root_combo_presentation` fija daño único, MP, Burning,
orden de transporte y cierre, mientras la aceptación del salto
`10752 -> 24894 -> 24895` sigue siendo obligatoriamente live.

Ante una futura regresión Combo, el orden de auditoría queda así:

1. igualdad de datos type 48;
2. requests exactos del cliente;
3. GCD/guard y feedback de rechazo;
4. resets de skill/tag;
5. orden de resultados y `SCPlotEvent` dentro del nodo;
6. sólo entonces modificar el runtime.

## Regresión live 2026-08-10: el guard legado no puede superar la cadencia AA8

La captura posterior al arreglo de orden
`aa8-game-20260810-234154357-session-3716780330.jsonl` demostró una carrera
adicional dentro de la misma sesión. El cliente pidió correctamente
`10752 -> 24894 -> 24895`, pero los primeros requests de `24895` llegaron a
75, 133 y 150 ms desde la aceptación de `24894` y recibieron
`SCSkillStarted(result=CooldownTime)`. El retry a ~166 ms sí fue aceptado. El
resultado visual era por ello intermitente: la tercera bola dependía de que el
cliente conservara el loop hasta superar el guard histórico fijo de 150 ms.

El compact AA8 cierra la contradicción sin inferencia:

- `24894/24895`: `auto_fire=1`, `custom_gcd=10`;
- Endless base `14835/14836/14837`: `auto_fire=1`, `custom_gcd=220`;
- Triple Slash Lightning: `custom_gcd=400/400/600`;
- Whirlwind Slash: `custom_gcd=200/500/200`.

El guard de AAEmu no puede imponer 150 ms sobre una etapa `auto_fire` cuya
cadencia AA8 explícita es menor. La resolución transversal queda:

```text
request_guard_ms = auto_fire && custom_gcd > 0
    ? min(150, custom_gcd)
    : 150
```

Esto no omite el GCD: después del guard se sigue comprobando
`GlobalCooldown`, cooldown propio, requisitos, rango y recursos. Tampoco
agenda, difiere ni reproduce casts. En Flamebolt las etapas instantáneas usan
10 ms; Endless y las cadenas Battlerage conservan el baseline de 150 ms ya
validado porque sus cadencias nativas son mayores.

Se añadió diagnóstico separado `reason=request_guard` y
`reason=global_cooldown`, con guard, tiempo transcurrido y `custom_gcd`, para
que una futura rama no vuelva a confundir ambas condiciones bajo el mismo
resultado wire `8`.

Validación previa al gate live:

- suite dirigida .NET 3.1: `43/43 PASS`;
- Flamebolt presentation: PASS,
  `2A9C46835C51CD7CBE11A4DD6F533DA53924A6C75DA2E1D5119FC410F8098C99`;
- Endless client-owned: PASS,
  `E733351A100156A45196A4C832738F4092DE47E75634A7A1CF8221AB36E3F756`.

## Estado supersedido: no existe admisión Combo custom en el runtime

La evidencia live posterior invalidó V6-V9 como arquitectura transversal. La
sesión UTC `aa8-game-20260811-000043728-session-136818707.jsonl` no contiene
ningún request de los hijos de Flamebolt ni rechazos que puedan ser resueltos
por un bypass o guard dinámico. La reparación basada en `auto_fire`, type 48 y
`custom_gcd` estaba intentando compensar una mutación anterior del transporte
de plots.

Regla promovida para las siguientes ramas:

1. type 48 describe selección/continuidad del cliente; el servidor no mantiene
   una máquina Combo paralela;
2. no cargar `auto_fire` en `SkillTemplate` para decidir admisión, feedback u
   orden de paquetes;
3. no reducir el guard histórico desde `custom_gcd` ni omitir GCD mediante una
   transición almacenada;
4. no suprimir globalmente `SCSkillStarted(CooldownTime)` ni clasificar su envío
   por rama;
5. no invertir globalmente `SCPlotEvent` y efectos para corregir una skill: el
   orden base probado en `835b42e1` es efectos primero y evento después;
6. una corrección de combat-sync que requiera otra presentación debe modelar la
   fase nativa concreta, no cambiar el contrato de todos los plots.

Se eliminaron también `enforce_gcd` y los fixtures Combo asociados del
Mechanics Lab. Eran instrumentación del sistema retirado, no evidencia nativa.
Triple Slash, Whirlwind y Endless vuelven a validarse en cliente por sus
requests, TlId, impactos y timestamps reales.

## Corrección 2026-08-10: retirar el guard legado y usar la autoridad type 41

La restauración completa del orden de `PlotNode` no cerró Flamebolt. La captura
wire `aa8-game-20260811-002109290-session-1246466874.jsonl` aportó el
contraejemplo que faltaba: el cliente sí pidió `10752 -> 24894 -> 24895`, pero
los requests de `24895` a 74, 91 y 112 ms desde `24894` recibieron
`SCSkillStarted(result=CooldownTime)`. El cuarto request, a 183 ms, fue
aceptado. La tercera bola dependía por tanto de que el loop cliente sobreviviera
al guard fijo de 150 ms; en las demás secuencias volvió a pedir sólo el root.

El compact AA8 ya contiene toda la autoridad temporal necesaria:

- Flamebolt root aplica `SpecialEffect type 41` de 1000 ms en su plot;
- `24894` y `24895` aplican type 41 de 10 ms;
- Endless base aplica type 41 de 200 ms en el primer nodo compartido;
- skills directas inician su `GlobalCooldown` en `Skill.Cast`.

El campo `custom_gcd` y los type 41 son datos nativos AA8; el filtro
`SkillLastUsed + 150 ms` era una protección genérica de AAEmu sin respaldo en
r558734. Mantener ambas autoridades imponía siempre el máximo implícito y hacía
imposible una cadencia nativa inferior a 150 ms.

La regla promovida queda simplificada: `Skill.Use` valida únicamente el
`GlobalCooldown` vigente, además del cooldown propio y los requisitos normales.
No existe guard paralelo, transición Combo servidor, allow-list, replay,
callback ni temporizador inferido. Los plots establecen su cadencia mediante el
type 41 que ya ejecutan; por eso retirar el guard no acelera Endless a la tasa de
sus requests anticipados.

Gate automatizado previo al despliegue: .NET Core 3.1 `620/620 PASS`. El cierre
live exige que el primer `24895` posterior a 10 ms sea aceptado y que Endless
continúe rechazando requests anteriores a sus 200 ms nativos.

## Evidencia binaria 2026-08-11: la arista padre define el estado de casteo

El commit `835b42e1` no era el control positivo exacto que se le había
atribuido: es posterior a la captura buena y ya contiene parte de la inversión.
El comparador autoritativo pasa a ser la DLL extraída de la imagen Docker
`sha256:c49c09ecbd...`, SHA-256
`EEC1E52B9B98F34CA77D6F8146252B3587A040402B50A69A4E57D4A03BCA947A`.

Su `PlotNode` demuestra una segunda dimensión cliente-visible distinta del
orden de paquetes: el actor de `SCPlotEvent` se decide por la arista que llevó
al evento (`ParentNextEvent`), no por una arista futura de `Event.NextEvents`.
Una arista padre `Casting` o `Channeling` significa que el evento completa o
atraviesa esa fase y debe llevar el caster; mirar hacia adelante adelanta el
estado un nodo y puede hacer que el cliente abandone una cadena type 48 aunque
el servidor no rechace ningún request.

Reglas reutilizables para próximas ramas:

1. comparar el artefacto ejecutado en la captura buena, no sólo un commit
   cercano;
2. tratar por separado orden del DD04, actor de `SCPlotEvent` y liberación
   `casting_useable`;
3. reconstruir `casting_useable` desde su opcode AA8 `0x159`; no inferirlo del
   actor del plot;
4. fijar con tests la dirección de cada relación del grafo: padre completado y
   siguiente programado no son equivalentes;
5. exigir requests wire de los hijos para cerrar una cadena cliente-owned.

Esta corrección es estructural y no contiene IDs, allow-lists, replay, timers
ni una máquina Combo servidor. Endless Arrows conserva exclusivamente su
type 41 nativo de 200 ms.

## Estado final promovido 2026-08-11

El cliente validó Flamebolt, Endless Arrows y Battlerage juntos sobre la imagen
`sha256:943967cb1395cfbe3b2efb258a07276543a91e7568e906ebff6369567acfa591`.
La traza `aa8-game-20260811-011526503-session-630269949.jsonl` registra dos
ciclos Flamebolt que llegan a resultados con `originSkill=24895`; la ejecución
visual confirmó root casteado más dos proyectiles instantáneos.

Contrato final:

1. type 48 es selección de continuidad del cliente;
2. type 41 es la autoridad GCD declarada por AA8;
3. el servidor no agenda, repite ni sintetiza hijos;
4. `SCPlotEvent.actor` describe la fase alcanzada mediante la arista padre;
5. `casting_useable 0x159` es un contrato independiente;
6. un cambio compartido sin evidencia AA8 se clasifica `custom-hypothesis` y
   no es desplegable.

Este checkpoint reemplaza como estado final todas las hipótesis intermedias de
guard dinámico, Combo servidor y reordenamiento condicional descritas arriba;
se conservan únicamente como evidencia negativa de diagnóstico.
