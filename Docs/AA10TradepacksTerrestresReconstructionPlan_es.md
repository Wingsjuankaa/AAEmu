# Plan AA10: reconstrucción de tradepacks terrestres

**Fecha de ejecución prevista:** 18 de agosto de 2026
**Target único:** `E:\AAEmu\rama_10\server\AAEmu`
**Branch:** `rama_10`
**Fork:** `Wingsjuankaa/AAEmu:rama_10`
**Padre obligatorio:** `upstream/client_version/zone-10.0.2_r575`
**Cliente:** ArcheAge Returns `10.0.2.13 r575`, x86-64

## 1. Objetivo y definición de terminado

Reconstruir y validar el flujo terrestre mínimo de tradepacks desde la creación
hasta el cobro, tomando como caso principal un pack fabricado en Dewstone
Plains y entregado en Solzreed Peninsula.

El dominio quedará listo cuando se demuestre, en una ejecución controlada, que:

1. el comprador correcto abre su lista sin cerrar el cliente;
2. el cliente y el servidor coinciden en packs aceptados, precio, ratio y
   frescura;
3. una entrega válida consume exactamente un pack y el labor correspondiente;
4. se crea exactamente la recompensa correcta, en la moneda y plazo correctos;
5. un rechazo no consume pack, labor, dinero ni crea correo;
6. repetir la misma petición no duplica la recompensa;
7. el resultado sobrevive a relog y, si la evidencia nativa exige persistencia
   del mercado, también a reinicio;
8. no aparecen cierres del cliente, opcodes desconocidos, excepciones fatales
   ni mutaciones parciales;
9. quedan pruebas automatizadas, evidencia y checkpoint actualizados.

## 2. Alcance de esta primera reconstrucción

### Incluido

- Tradepacks terrestres normales fabricados por el jugador.
- Ruta principal Dewstone Plains (`zone_group_id=3`) → Solzreed Peninsula
  (`zone_group_id=5`).
- Comprador de oro de Solzreed: NPC template `17971`,
  `specialty_bundle_id=10`.
- Pack equipado, pack almacenado/transportado en vehículo y transición entre
  ambos estados.
- Lista del comprador, detalle/precio, entrega, labor, correo, reparto al
  crafter, ratio de mercado y frescura.
- Rechazos y repetición segura.

### Fuera de alcance salvo dependencia probada

- Cargo marítimo y compra de cargo en el outlet.
- Comercio entre continentes, pescado, reliquias y packs de instancia.
- Butler/family trade jobs y automatización de entregas.
- Eventos globales de specialty y balance definitivo de toda la economía.
- El comprador alternativo de Solzreed que paga otra moneda
  (`npc_id=15087`, bundle `26`), salvo como prueba negativa.

No se ampliará el alcance por semejanza. Si el cliente demuestra que una
primitiva compartida es indispensable, se documentará antes de implementarla.

## 3. Estado conocido al 17 de agosto

### Hechos observados por el usuario

- El pack pudo fabricarse en Dewstone Plains.
- El pack pudo transportarse en un vehículo.
- La entrega en Solzreed falló.
- Al intentar después inspeccionar el detalle del NPC, el cliente se cerró.

### Hechos comprobados en el runtime y los datos AA10

- `SpecialtyManager` carga correctamente al arrancar: 81 rutas, 4.256 filas de
  bundle, 38 NPCs, 3 cargo goods y 5 índices de precio.
- Solzreed contiene dos NPCs specialty distintos:
  - `17971`, bundle `10`, pago normal en oro;
  - `15087`, bundle `26`, pago mediante el item `23633`.
- Dewstone posee 11 templates con `specialty_zone_id=3`; sólo 7 están mapeados
  al bundle `10`: `31833`, `31856`, `31896`, `37467`, `49043`, `49080` y
  `49093`. Los templates `20099`, `24932`, `24933` y `26478` no son aceptados
  por ese bundle en la SQLite retail/full r575.
- El bundle `10` contiene 110 ofertas positivas. La implementación actual las
  emite en 6 páginas de `SCSpecialtyGoodsPacket` de hasta 20 entradas.
- Los packs terrestres modernos usan `item_backpacks.backpack_type_id=3`.
- Los packs frescos de Dewstone usan `freshness_group_id=5`; sus tramos son
  115%, 105%, 90%, 85% y 65% según antigüedad.
- Los packs añejados sin aditivos usan `freshness_group_id=9`; sus tramos son
  82%, 115%, 105%, 88% y 65%.
- `BackpackTemplate` no carga hoy `freshness_group_id` y
  `SpecialtyManager.SellSpecialty` no incorpora `freshness_group_items` al
  cálculo. El packet de doodad hacia Zone escribe actualmente
  `freshnessTime=0`.
- La única prueba específica de `SpecialtyManager` sólo comprueba que su
  constructor no invoque dependencias.
- La venta actual crea/envía correo antes de intentar consumir el pack. Si el
  consumo falla, existe riesgo de recompensa emitida con el pack todavía
  presente. Un fallo del correo al crafter también permite continuación
  parcial.

### Evidencia del cierre de sesión

En la sesión inspeccionada, a las `01:18:48` el servidor ya había emitido
`SCLeaveWorldGrantedPacket` cuando recibió un movimiento tardío. El método de
logging `CSMoveUnitPacket.Verbose()` dereferenció `ActiveChar.ParentWorld` y
produjo un `NullReferenceException`; la desconexión llegó un segundo después.

Ese error es real, pero por su orden temporal parece una consecuencia del
abandono del mundo, no la causa demostrada del cierre. En los logs conservados
no aparece una recepción de `CSListSpecialtyGoodsPacket` (`0x071`) ni de
`CSSellBackpackGoodsPacket` (`0x06F`) durante ese intento. Por ello no se debe
parchear todavía el flujo de venta basándose sólo en esa excepción.

## 4. Hipótesis ordenadas, no conclusiones

1. El pack seguía en el vehículo y no estaba equipado en el slot Backpack; el
   servidor sólo vende el pack equipado y debe rechazar limpiamente el otro
   estado.
2. Se usó el NPC/bundle alternativo o un template antiguo no mapeado.
3. `SCSpecialtyGoodsPacket` o su paginación/campos no coincide con el consumer
   nativo r575 y el cliente falla al abrir o inspeccionar la lista.
4. La frescura ausente o serializada como cero deja inconsistente el detalle,
   el precio o el lifecycle del pack.
5. La petición llega correctamente, pero la validación de NPC, distancia,
   `characterObjId`, bundle o zona la rechaza sin trazabilidad suficiente.
6. La entrega entra al servidor y falla durante correo, consumo, labor o
   persistencia, dejando una mutación parcial.
7. El cierre pertenece a World/Zone/movimiento y sólo coincide temporalmente
   con la prueba de comercio.

Cada hipótesis se cerrará con packet/log/data concretos. No se aceptará “dejó de
cerrarse” como prueba del contrato.

## 5. Fases para mañana

### Fase 0 — Congelar el caso y preparar rollback (30–45 min)

1. Guardar logs Game, World/Zone y timestamps de la sesión antes de que roten.
2. Registrar branch, HEAD, estado dirty, hashes del compact montado, SQLite
   full, `x2game.dll` y binarios Zone.
3. Identificar el caso exacto:
   - personaje;
   - item instance ID y template ID;
   - `CreateTime`, `MadeUnitId`, freshness group;
   - slot/owner actual: espalda, vehículo o doodad;
   - NPC object ID, template ID, interacción y posición;
   - zone ID y zone group del jugador y del NPC.
4. Respaldar únicamente las filas afectadas de inventario, correo y estado del
   personaje necesarias para comprobar antes/después. No modificar `.env` ni
   insertar items directamente en MySQL.
5. Fijar un marcador de correlación visible por intento y numerar las pruebas.

**Gate G0:** no avanzar sin conocer pack, NPC, owner/slot y timestamp exactos.
Si el pack original ya no existe, reproducir una sola vez con un pack fresco
conocido del bundle 10, preferentemente `31856`, conservando su creación
normal.

### Fase 1 — Cerrar la relación de datos AA10 (45–75 min)

Construir un dossier reproducible desde full DB y compact retail, ambos en modo
read-only:

```text
craft -> item -> item_backpack -> freshness_group/items
      -> specialty_zone -> route 3→5 -> bundle item
      -> specialty NPC 17971/bundle 10 -> currency/mail
```

Comprobar expresamente:

- receta, producto y `CreateTime` real de craft;
- `item_prices.refund`, `specialty_bundle_items.profit/ratio`;
- pertenencia exacta al bundle del NPC;
- `item_backpacks.backpack_type_id` y `freshness_group_id`;
- límites inclusivos/exclusivos de cada tramo de frescura;
- `seller_share_ratio` y su relación con el reparto seller/crafter;
- ruta `specialties` 3→5;
- flags, interaction set, spawn y mirror del NPC efectivo;
- concordancia full/compact para todas las filas consumidas.

Si falta una fórmula, consumer, serializer o lifecycle, abrir una frontera
forense AA10 concreta sobre:

- `x2ui/specialty/sell_tradegood.alb` e `info.alb`;
- consumer nativo de `SCSpecialtyGoods`/detalle;
- serializer de la quote y callbacks de venta;
- cálculo de freshness y payout;
- orden de resultado, item task, correo y refresh.

**Gate G1:** dossier con SQL, filas, schema, procedencia y gaps explícitos. No
portar una fórmula AA8 ni adivinar límites de tiempo.

### Fase 2 — Reproducir y separar UI, protocolo y venta (60–90 min)

Usar el perfil normal del Control Center y las Zones necesarias para el cruce
Dewstone–Solzreed. Verificar `ZoneLoaded` y heartbeats antes de abrir el
cliente. Ejecutar una interacción por vez:

| Prueba | Estado | Acción | Resultado esperado |
|---|---|---|---|
| R1 | Sin pack | Abrir comprador 17971 | Lista válida; venta rechazada sin mutación |
| R2 | Pack compatible en vehículo | Abrir lista e intentar vender | Rechazo explícito; cliente estable |
| R3 | Pack compatible equipado | Sólo abrir lista/detalle | UI estable y precio coherente |
| R4 | Pack compatible equipado | Vender una vez | Una transacción completa |
| R5 | Misma petición repetida | Reenviar/segundo clic | Sin doble consumo ni doble correo |
| R6 | Pack no mapeado | Intentar vender | Rechazo explícito y limpio |
| R7 | NPC 15087/bundle 26 | Abrir/intentar | Resultado propio del bundle; sin cierre |
| R8 | Fuera de rango/target falso | Intentar vender | Rechazo sin mutación |

Para cada intento correlacionar:

```text
interacción NPC
  -> CSListSpecialtyGoods 0x071
  -> SCSpecialtyGoods 0x0C6 (begin/middle/end + quotes)
  -> selección/detalle cliente
  -> CSSellBackpackGoods 0x06F
  -> validación y resultado
  -> ItemTask SellBackpack + labor + mail + resync
```

Registrar bytes, longitud, packet level, IDs y orden; no inundar los logs con
movimiento global. Confirmar contra el consumer r575:

- orden y ancho de los dos counts;
- orden de flags `isBegin/isEnd`;
- cuerpo exacto de cada `SpecialtyQuote`;
- significado/unidad de `Refund`, `NoEventRefund`, `Ratio`, `Stock`,
  `CanProduce`, `Currency` y `Type`;
- semántica de 6 páginas para las 110 entradas del bundle 10;
- si el detalle necesita freshness/creation time adicional.

**Gate G2:** ubicar el primer punto divergente. Si el cliente abandona antes de
`0x071`, detener la rama specialty y aislar interacción/World/Zone. Si recibe
`0x0C6` y cae al procesarlo, cerrar primero el wire. Si llega `0x06F`, seguir a
la transacción.

### Fase 3 — Implementar la clausura mínima de datos y wire (60–120 min)

Implementar sólo lo confirmado por G1/G2:

1. Cargar `freshness_group_id` en la plantilla de backpack y crear el catálogo
   tipado mínimo de `freshness_groups`/`freshness_group_items`.
2. Resolver la etapa desde `Item.CreateTime` con UTC, límites y fallback
   probados; preservar el tiempo al mover el pack entre espalda, vehículo y
   doodad.
3. Corregir la serialización de freshness en Game/World/Zone donde el consumer
   r575 la exija; eliminar ceros ficticios sólo cuando exista el contrato.
4. Corregir quote, filtrado y paginación de la lista según el cliente nativo.
5. Añadir rechazo explícito para pack no equipado, bundle incorrecto, template
   no aceptado, target inválido, zona incorrecta y distancia excesiva.
6. Añadir logging temporal correlacionado en los puntos exactos y retirarlo al
   cerrar el diagnóstico.

AA8 se usará únicamente para localizar formas candidatas. Cada parte se
clasificará como `generic_x64_compatible`,
`aa10_confirmed_shared_primitive`, `structural_candidate`,
`version_sensitive_blocked` o `aa8_only`.

**Gate G3:** la lista y el detalle se abren de forma repetible sin cierre y sus
valores coinciden con la evidencia AA10.

### Fase 4 — Hacer atómica e idempotente la entrega (90–150 min)

Reestructurar la venta como una sola operación planificada:

```text
snapshot -> validar -> calcular -> preparar mutaciones
         -> commit atómico -> packets/resultados/resync
```

La snapshot debe fijar item instance/template, owner, slot, `CreateTime`,
`MadeUnitId`, NPC, bundle, zona, distancia, labor y ratio de mercado. Antes del
commit se vuelve a comprobar que el mismo pack sigue equipado.

El cálculo debe separar y probar:

```text
base item refund + bundle profit/ratio
-> ratio de mercado de la ruta/destino
-> freshness reward rate
-> bonus/interés confirmado
-> seller/crafter share confirmado
-> moneda y redondeo nativos
```

La persistencia de consumo, labor, correo(s) y contador/ratio de mercado no
puede dejar estados parciales. No enviar correo irreversible antes de asegurar
el consumo. No implementar compensaciones por ID ni un state machine paralelo;
usar la transacción/persistencia existente o ampliar su clausura mínima.

La segunda ejecución, la concurrencia y una respuesta perdida deben encontrar
el pack ya consumido y no recompensar nuevamente.

**Gate G4:** éxito y todos los rechazos dejan invariantes demostrables antes y
después, incluyendo fallos inyectados de correo, persistencia y consumo.

### Fase 5 — Pruebas automatizadas (60–120 min)

Añadir como mínimo:

#### Datos y cálculo

- carga de freshness group y etapas;
- bordes exactos de `900`, `3600`, `10800`, `86400`, `172800`, etc.;
- pack sin grupo de frescura;
- mapeo Dewstone→Solzreed aceptado y no aceptado;
- fórmula, unidades y redondeo de oro/moneda alternativa;
- seller/crafter share y crafter igual/diferente al vendedor.

#### Wire

- golden bytes de `SpecialtyQuote`;
- lista vacía, una página, 20 entradas y 110 entradas;
- flags begin/middle/end y límites máximos;
- request `0x071`, sell `0x06F` y respuesta `0x0C6` con packet level correcto;
- freshness/timestamps en los serializers que correspondan.

#### Transacción

- éxito único;
- sin pack, pack en vehículo, bundle incorrecto y NPC incorrecto;
- distancia, zone group y `characterObjId` inválidos;
- labor insuficiente;
- fallo de correo, consumo y persistencia sin mutación parcial;
- doble clic, repetición y carrera sobre el mismo item instance;
- relog posterior al éxito y al rechazo.

Ejecutar los gates del repositorio:

```powershell
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore
```

Ejecutar además las integraciones specialty sólo con DB/runtime declarados. Si
se genera o altera una SQLite de runtime, exigir `quick_check` e
`integrity_check`.

**Gate G5:** suite verde, tests specialty con cobertura positiva/negativa y
ninguna regresión de inventario, correo, labor, movimiento o World/Zone.

### Fase 6 — Validación jugable controlada (45–90 min)

1. Desplegar sólo Game/World/Zone afectados mediante Control Center, con
   rollback de imagen/config/datos preparado.
2. Confirmar hashes montados, salud de DB/Login/Game y todas las Zones del
   recorrido.
3. Para la primera prueba usar un pack fabricado normalmente. Para repeticiones
   diagnósticas puede usarse `give-test-items.ps1`, validando template, slots y
   el efecto de `CreateTime`; no insertar en MySQL ni publicar Web API `1280`.
4. Reducir temporalmente el retraso del correo sólo mediante el comando/runtime
   soportado y restaurarlo después.
5. Ejecutar R1–R8 de a una, inspeccionando logs y persistencia antes de autorizar
   el paso siguiente.
6. Tras R4 comprobar:
   - pack ausente de espalda/vehículo/inventario;
   - labor descontado una vez;
   - un correo, moneda, importe, reparto y delay correctos;
   - ratio/frescura mostrados iguales al cálculo autoritativo;
   - estabilidad al relog.
7. Repetir la ruta principal una segunda vez desde craft para descartar que el
   éxito dependa del estado inicial.

**Gate G6:** dos entregas normales exitosas, matriz de rechazos limpia, ningún
cierre del cliente y cero errores nuevos de protocolo/persistencia.

### Fase 7 — Cierre y documentación (30–45 min)

- Retirar flags, mensajes y logging temporal.
- Restaurar delay/configuración de prueba y cualquier artefacto instrumentado.
- Actualizar checkpoint y manifest del dominio con SQL, hashes, packets,
  pruebas, commit AA8 consultado y clasificaciones.
- Registrar gaps no terrestres como pendientes separados, sin declararlos
  resueltos.
- Dejar rollback probado y un runbook corto para repetir Dewstone→Solzreed.
- Revisar diff para no mezclar los 16 cambios locales preexistentes.

## 6. Árbol de decisión durante la ejecución

```text
¿El cliente envía CSListSpecialtyGoods 0x071?
├─ No -> aislar interacción NPC / World / Zone; no tocar la venta
└─ Sí
   ¿SCSpecialtyGoods 0x0C6 coincide con el consumer y la UI queda estable?
   ├─ No -> cerrar packet body, paginación, quote y freshness
   └─ Sí
      ¿Llega CSSellBackpackGoods 0x06F?
      ├─ No -> aislar estado del pack, selección UI y target
      └─ Sí
         ¿Falla antes de mutar?
         ├─ Sí -> datos/NPC/bundle/distancia/labor con error explícito
         └─ No -> cerrar atomicidad, persistencia, correo y resync
```

El `NullReferenceException` de `CSMoveUnitPacket.Verbose()` se corregirá como
defecto defensivo separado si vuelve a aparecer, protegiendo el logging cuando
`ActiveChar` o `ParentWorld` ya no existen. No se presentará como reparación de
tradepacks salvo correlación nueva que pruebe causalidad.

## 7. Orden sugerido de la jornada

| Bloque | Resultado que debe quedar |
|---|---|
| Inicio | G0: evidencia congelada y caso exacto identificado |
| Mañana temprana | G1–G2: causa localizada en datos, wire, UI o transacción |
| Mediodía | G3: lista/detalle estable y freshness cerrado |
| Tarde | G4–G5: entrega atómica con pruebas automatizadas |
| Final | G6–G7: prueba jugable, rollback y checkpoint |

Si G2 abre una frontera nativa grande, el objetivo del día cambia a cerrar esa
frontera con evidencia y golden bytes; no se desplegará una aproximación para
cumplir el horario.

## 8. Criterio de commit y entrega

El cambio final debe ser pequeño y separable:

1. datos/modelo freshness;
2. wire/UI specialty si fue necesario;
3. transacción de venta;
4. tests;
5. checkpoint/documentación.

No hacer cherry-pick de AA8, no actualizar el upstream sin petición expresa,
no hacer force-push y no incluir `.env`, dumps, SQLite grandes, logs ni cliente.
