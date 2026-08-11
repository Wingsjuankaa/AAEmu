# Checkpoint AA8 — autoridad y protocolo de cooldown

Fecha: 2026-08-09  
Origen del hallazgo: cierre Battlerage V5–V9  
Autoridad: Kakao 8.0.3.12 r558734, Stage 15 y captura viva

## Regla reusable

Un cooldown es estado autoritativo con operaciones diferentes; no es un timer
visual que pueda reiniciarse para representar cualquier cambio. Toda rama
nueva debe separar:

1. `StartCooldown`: una sola vez por lanzamiento aceptado, deduplicado por
   `TlId/castToken`;
2. `GetRemaining`: lectura contra el reloj común;
3. `ReduceCooldown`: opera sobre el tiempo restante, con clamp a cero;
4. `ResetCooldown`: elimina el estado de forma explícita;
5. snapshot: restaura estado durante login/reconexión, no refresca cada cast.

Reducción, reset, inicio y snapshot no son intercambiables ni en runtime ni en
wire.

## Contrato AA8 probado

- `SCSkillCooldownReducePacket 0x038`, transporte cifrado nivel 5:
  `BC + skill(i32) + tag(i32) + percent(u32) + count(u32) + reduce(u32) + 3 bool`.
- `SCCooldownsPacket 0x34D`, transporte cifrado nivel 5: tres buckets de hasta
  150 entradas con `id/duration/remaining` de 32 bits.
- `SCSkillCooldownResetPacket 0x098` permanece una operación distinta.
- `SpecialEffect type 153` selecciona por skill/tag y transporta reducción
  flat/porcentual; la reducción se aplica al restante.

Los niveles de transporte de Modern fueron falsificados para AA8: publicar
`0x34D/0x038` en nivel 1 desconectó al cliente al entrar. Un serializer o
nombre equivalente no autoriza a copiar framing, anchuras ni lifecycle 10.x.

## Lifecycle de plots

Una skill `plot_only` inicia cooldown cuando el servidor acepta el cast. El
fin del plot no puede volver a iniciarlo ni emitir un snapshot masivo.

Charge `11918` probó el defecto: el cooldown se iniciaba al recibir
`SCPlotEnded`, 406–417 ms después del request, y el cliente volvía a mostrar
12 segundos. Tras mover el inicio al cast y deduplicarlo por `TlId`, el
snapshot determinista a 410 ms conserva aproximadamente 11.590 ms.

`SCCooldowns 0x34D` queda reservado a restauración. Una reducción incremental
viaja por `0x038`; un reset real viaja por `0x098`.

## Reducción por impacto

Behind Enemy Lines: Gale `39661` aporta el caso de referencia:

- target: Charge `11918`;
- reducción: 2.000 ms;
- una aplicación por objetivo distinto impactado con éxito;
- miss, requisito fallido o impacto duplicado sobre el mismo objetivo: no-op;
- progresión aceptada: `12.000 → 10.000 → 8.000 → 6.000 ms`.

La relación se consume después de confirmar el impacto. Nunca se usa un reset
para simular la reducción.

## Feedback y barra cliente

Un request duplicado durante un cooldown real no debe recibir
`SCSkillStarted(CooldownTime)`: AA8 puede interpretar ese resultado como un
nuevo lifecycle y reiniciar la barra. La excepción estrecha para loops
`auto_fire` sin cooldown propio está documentada en
`CHECKPOINT_AA8_COMBO_GCD_ADMISSION_V1.md`.

Si el salto visual coincide con la salida de un buff, no asumir que la retirada
mutó el cooldown. Auditar, en orden:

1. el packet de creación del buff y sus vínculos funcionales;
2. inicios duplicados por callbacks de plot;
3. snapshots fuera de login/reconexión;
4. respuestas `CooldownTime` a reintentos;
5. reducción/reset reales.

Charge demostró que el causante final era un vínculo toggle incorrecto creado
segundos antes, no `SCBuffRemoved`; véase
`CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md`.

## Evidencia negativa preservada

- reiniciar el cooldown para mostrar una reducción: incorrecto;
- iniciar una skill `plot_only` al cerrar el plot: incorrecto;
- enviar `SCCooldowns` al terminar cada plot: incorrecto;
- copiar nivel de transporte Modern: desconecta AA8;
- atribuir una coincidencia temporal con `SCBuffRemoved` como causalidad:
  falsificado;
- silenciar globalmente todo `CooldownTime`: rompe loops cliente sin cooldown
  propio.

## Gate obligatorio para ramas futuras

- inicio único por cast;
- segundo uso y request duplicado;
- reducción flat, porcentual, por tag y clamp a cero;
- reset separado;
- skill directa y `plot_only`;
- snapshot tras reconexión;
- expiración simultánea de buffs relacionados/no relacionados;
- captura viva de la barra durante todo el lifecycle.

## Enmienda live: reset sin delta corrompe cadenas Combo

Flamebolt base `10752` reveló una segunda frontera del protocolo. Con el modo
GM `IgnoreSkillCooldowns` activo, el cierre de cada plot llamaba a
`ResetSkillCooldown` incluso cuando la skill declara `cooldown_time=0`. La
implementación enviaba de todos modos dos `SCSkillCooldownResetPacket 0x098`:
uno por skill y otro por su tag `3308`.

El cliente no trató esos paquetes como un no-op visual. El reset del tag borró
el estado de la cadena cliente `10752 -> 24894 -> 24895`; mientras se mantenía
la tecla sólo volvió a solicitar `10752`, repitiendo el casteo inicial y
perdiendo las dos bolas instantáneas. La traza previa mostró inmediatamente
después de cada `SCPlotEnded`:

```text
SCSkillCooldownResetPacket
SCSkillCooldownResetPacket
AA8CooldownReset ... skill=10752 tags=[3308]
```

Regla promovida: `ResetCooldown` sólo puede emitir `0x098` cuando el selector
eliminó al menos un cooldown autoritativo todavía activo. Si el reset por skill
es no-op, no se expande a sus tags y no se publica ningún paquete. Un reset por
tag requerido por una mecánica debe solicitarse explícitamente con ese
selector. Esto conserva `IgnoreSkillCooldowns` para timers reales sin mutar
máquinas de estado cliente asociadas a tags de Combo.

La regresión queda cubierta por `CooldownResetTests` y por el gate conjunto de
Sorcery, cooldown y Combo. El compact AA8 confirma para `10752`:
`cooldown_time=0`, `cooldown_tag_id=3308`, `auto_fire=1`; los hijos
`24894/24895` también tienen cooldown cero.
