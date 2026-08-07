# Protocolo de aceptación en vivo Sorcery AA8 V2

Cliente: ArcheAge Kakao `8.0.3.12 r558734`  
Runtime: `compact-8.0-runtime-transversal-sorcery-v10.sqlite3`  
SHA-256: `FB77DC60360C1BF5B9D683C945CD11FCA4736034B75EB16D1C5C4FBBFF065876`

## Objetivo y preparación

Este protocolo cierra lo que no puede probar un test de servidor: UX,
animación, FX, sonido, física del cliente, limpieza visual, repetición y
persistencia.

1. Entrar con sesión limpia, Sorcery nivel suficiente y sin cooldowns.
2. Tomar captura de skills, MP, Magic Source, buffs y barra de acciones.
3. Usar primero un NPC aislado y después tres o más NPCs no vinculados a quest.
4. Probar una skill por vez y repetirla cuando termine el cooldown.
5. Si hay desconexión, barra bloqueada, movimiento duplicado o doodad huérfano,
   detener esa familia y conservar los logs inmediatamente.

Blanco inerte aprobado para esta rama:

```text
/spawn npc 13013
```

Es un template nivel 50, hostil, sin EXP y con `ai_file_id=25 (Dummy)`. No usar
`15813`: pese a su apariencia de training dummy, selecciona la IA
`HoldPosition` y responde al daño. Para limpiar el blanco aprobado:

```text
/despawn npc 13013 30
```

Para acompañar una prueba fallida:

```powershell
docker compose logs --since 10m game > sorcery-live-failure.log
```

La imagen de validación incorpora la traza estructurada
`[AA8SorceryLive]`. No altera gameplay y cubre los 43 IDs del cierre V3. Al
terminar cada bloque, generar el resumen reproducible:

```powershell
docker compose logs --no-color --since 30m game |
  python reconstruccion_skills_8\sorcery\summarize_sorcery_live_trace_v1.py `
    --output-json E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-v1.json `
    --output-csv E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-v1.csv
```

El estado basal persistente de Dannia/owner 1 está congelado en
`E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\baseline-owner-1.json`.
Después del relog se debe ejecutar `snapshot_sorcery_persistence_v1.py` y
comparar activas, niveles, seis pasivas, active types y selecciones Heir. Ver
`CHECKPOINT_SORCERY_LIVE_TRACE_V1.md`.

La evidencia manual se registra en
`generated/sorcery-live-acceptance-ledger-v1.json`. Para cada ID sólo se cambia
un gate a `confirmed` cuando `evidence` contiene la captura, video o referencia
de sesión correspondiente. No se reutiliza una evidencia de otra skill y no se
marca `relog` antes de repetirla en una sesión nueva.

## Matriz base obligatoria

| Estado | ID | Skill | Contrato visible mínimo |
|---|---:|---|---|
| ☑ | 10151 | Freezing Earth | Confirmada en V10: AoE, daño, buffs, cuatro ejecuciones limpias y relog |
| ☐ | 10153 | Insulating Lens | escudo correcto; Absorption una vez; Ice Shard/Snare al romper; cooldown final de 30 s |
| ☐ | 10664 | Meteor Strike | casteo, AoE, Trip y desplazamiento reconciliado sin doble movimiento |
| ☐ | 10667 | Freezing Arrow | proyectil, impacto único, slow y cooldown |
| ☐ | 10670 | Arc Lightning | casteo, daño/Shock y propagación cercana sin golpear al caster |
| ◐ | 10752 | Flamebolt | mantener pulsado: cadena cliente `10752→24894→24895`, Burning y barra liberada al terminar; visual y segundo uso confirmados, falta relog |
| ☐ | 11314 | Frigid Tracks | huellas, freeze al cruzar y limpieza de todas las huellas |
| ☐ | 11939 | Searing Rain | área de 10 m, multi-tick durante 7 s y segunda ejecución activa |
| ☐ | 11967 | Chain Lightning | hasta cinco saltos y daño decreciente por salto |
| ☐ | 12796 | Magic Circle | doodad orientado, buff al entrar/salir, recurso/protocolo y desaparición |
| ☐ | 14774 | Flame Barrier | pared/área, ticks, slow y desaparición sin área invisible |
| ☐ | 23593 | Gods' Whip | cinco pasos, coste/daño creciente, transiciones de doodad y cierre limpio |

En cada fila registrar: MP y Magic Source antes/después, daño/ticks, cooldown,
start/fire/end, FX/sonido, control del personaje y resultado de la repetición.

Para Flamebolt no se esperan tres proyectiles con un clic aislado. Mantener la
misma tecla hace que el cliente solicite las etapas `10752`, `24894` y `24895`
usando los dos descriptores `Combo` de `1000 ms`. El servidor debe aceptar una
sola vez cada etapa válida; los reintentos por tecla mantenida pueden responder
`CooldownTime`, pero no pueden generar proyectiles, daño ni coste adicionales.

## Gates de riesgo alto

### Insulating Lens (`10153`)

1. Lanzar y anotar carga visible/MP.
2. Confirmar inmunidad a Trip mientras corresponde.
3. Recibir daño controlado menor que la carga: no debe dispararse Ice Shard.
4. Romper el resto con un golpe: la explosión/Snare debe ocurrir exactamente
   una vez y el daño excedente debe atravesar el escudo.
5. Recibir otro golpe inmediato: no debe repetir el trigger.
6. Confirmar que el cooldown de 30 s comienza al terminar el escudo y que la
   skill vuelve a estar disponible después.
7. Repetir dejando expirar el buff para distinguir `Timeout` de `Absorption`.

### Fire Wall: Mist (`41223`) y `SkillUse.value4`

1. Seleccionar Mist, apuntar a una posición A y lanzar.
2. Mover el cursor y el personaje a una posición B antes de la fase hija.
3. Confirmar que la hija `41478` aparece en A, anclada a la pared, no en B ni
   sobre el caster.
4. Confirmar duración, daño/control y limpieza del área.
5. Repetir tras cooldown. `value4=1` no debe causar una segunda skill, cambiar
   el target ni duplicar la ejecución.

### Magic Circle y retornos contextuales (`42012/43464/43465`)

Estas tres skills son entrypoints nativos con `show=0`: el cliente debe
exponerlas de forma contextual, no como botones normales aprendibles.

1. Lanzar Magic Circle base `12796`, alejarse claramente del centro y usar la
   acción contextual `42012`.
2. Confirmar un único blink a la posición capturada, dentro del mismo
   mundo/instancia; el buff/tag `4294` debe consumirse por el Dispel posterior.
3. Confirmar que la acción no puede reutilizar un ancla ya consumida.
4. Repetir con Flame `43068` y su retorno `43464` (buff de posición `25850`).
5. Repetir con Quake `43185` y su retorno `43465` (buff de posición `25851`).
6. Cambiar de instancia o mundo antes de intentar el retorno: debe rechazarse
   sin mover al personaje ni dejarlo bloqueado.

Los tests de servidor comprueban la resolución del ancla y el rechazo entre
instancias; esta sección certifica la aparición contextual, blink, FX y
consumo en el cliente real.

### Skills internas de login-stage (`12789/12790/12791`)

Se auditan estructuralmente porque son raíces nativas Sorcery, pero no se
fuerzan al skillbook del mundo. Registrar durante acceso/creación si el cliente
ejecuta las previews Flamebolt, Freezing Arrow y Raging Thunder sin error de
paquete, desconexión o placeholder visual.

### Casting, channeling y scheduler

1. Interrumpir una vez Flamebolt, Arc Lightning y Meteor durante casting;
   ninguna debe ejecutar su impacto después de la interrupción.
   Para cada intento registrar que el cliente envía `CSStopCastingPacket`, el
   servidor termina con `plot_ended ... cancelled=True` y no aparecen coste,
   evento de impacto ni `SCUnitDamagedPacket` posteriores para el mismo `tlId`.
   El paquete AA8 contiene `skillTlId` y `plotTlId`; las skills plot-only deben
   cancelarse contra el segundo y las basadas en `SkillTask` contra el primero.
2. Ejecutarlas normalmente y confirmar un solo `start/fire/end`.
3. Repetir Searing Rain, Flame Barrier y Gods' Whip varias veces para verificar
   que ningún tick desaparece por colisión de jobs y que no queda un job viejo.

## Matriz Heir obligatoria

Para cada familia seleccionar el primer sucesor, lanzar, seleccionar el
segundo, lanzar, volver a selección de personaje y comprobar persistencia.

La progresión AA8 desbloquea estas familias por pasos. La entrada inicial a
Ancestral usa `1 x item 40491`; después, los seis gates Sorcery quedan
disponibles en niveles Ancestral `1`, `4`, `7`, `10`, `13` y `16`:

| Ancestral mínimo | Heir | Familia |
|---:|---:|---|
| 1 | 19 | Flamebolt |
| 4 | 20 | Chain Lightning |
| 7 | 21 | Meteor Strike |
| 10 | 40 | Gods' Whip |
| 13 | 52 | Flame Barrier |
| 16 | 58 | Magic Circle |

| Estado | Familia base | Heir | Sucesor A | Sucesor B |
|---|---:|---:|---:|---:|
| ☐ | 10752 Flamebolt | 19 | 36474 | 36475 |
| ☐ | 11967 Chain Lightning | 20 | 36476 | 36477 |
| ☐ | 10664 Meteor Strike | 21 | 36478 | 36479 |
| ☐ | 23593 Gods' Whip | 40 | 39669 | 39674 |
| ☐ | 14774 Flame Barrier | 52 | 41222 | 41223 |
| ☐ | 12796 Magic Circle | 58 | 43068 | 43185 |

Por familia:

1. deben aparecer exactamente dos sucesores;
2. sólo el seleccionado debe poder lanzarse;
3. el cambio debe producir confirmación visual y no duplicar active types;
4. relog debe preservar selección;
5. probar reset por sucesor, por ability y total;
6. reloguear después de cada tipo de reset.

### Primera transición ancestral y punto de parada

El flujo de compra de Honor y ascenso pertenece al otro frente. Cuando éste
termine, guardar y reloguear antes de seleccionar una variante. No modificar
las seis familias de una vez.

Primera interacción autorizada:

1. confirmar Ancestral `>=1`, Sorcery activa y Flamebolt base `10752`
   aprendida;
2. seleccionar únicamente Heir `19` sucesor `36474` con creación, no cambio;
3. lanzarlo una sola vez contra el dummy seguro `13013`;
4. detener la prueba sin seleccionar `36475`, resetear ni reloguear;
5. preservar logs y revisar `Success`, lifecycle, coste, daño, active type y
   fila persistida antes de autorizar la segunda variante.

Sólo después de ese control se selecciona `36475` con `isChange=true`, se
lanza una vez y se repite la revisión. El relog y los tres tipos de reset se
prueban después, manteniendo una única familia activa. Una desconexión, skill
base todavía lanzable como si fuera la seleccionada, ambas variantes activas,
duplicación de coste/daño o pérdida de selección detiene toda la matriz Heir.

## Pasivas y persistencia

Marcar las seis pasivas `15, 38, 99, 257, 258, 301` una por una:

- ☐ se pueden aprender al cumplir puntos;
- ☐ el buff/estadística visible cambia inmediatamente;
- ☐ al resetear desaparece el efecto;
- ☐ después de relog permanecen sólo las aprendidas.

Al finalizar toda la matriz:

1. salir a selección de personaje y volver;
2. repetir Freezing Earth, Insulating Lens, Searing Rain, Magic Circle,
   Fire Wall: Mist y Gods' Whip;
3. confirmar nivel, puntos, pasivas, Heir y barra de acciones;
4. cerrar sesión limpiamente, volver a entrar y comprobar que no queda cooldown
   permanente, doodad huérfano, buff fantasma ni recurso fuera de rango.

## Criterio de cierre

Sorcery queda aceptada completamente en vivo sólo cuando todas las casillas
están aprobadas, el resumen no conserva raíces aplicables en
`not_observed`/`rejected_only`/`partial_lifecycle` y ningún segundo uso o relog
altera el resultado. `server_lifecycle_complete` no reemplaza la evidencia
visual. Ante un
fallo, registrar ID, captura/video, target usado, MP/recurso, cooldown y log;
el diagnóstico debe limitarse al closure de esa familia.

El gate final lo calcula `build_sorcery_completion_audit_v2.py`: exige 30/30
lifecycle actuales, 30/30 gates visual/repetición/relog y un snapshot
post-relog consistente. El estado `complete` no puede editarse manualmente.
