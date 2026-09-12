# Reconstrucción de Lluvia de flechas: Neblina — AA10 r575

Actualización posterior con videos del usuario: ver `AA10NeblinaDirection_es.md`.
La reaparición de flechas fue confirmada; se corrigió después su elevación
artificial. Los resultados y hashes de este documento corresponden a la primera entrega.

Fecha: 2026-09-11. Skill 36473, plot 2957. Target `rama_10`, HEAD de partida
`fd53b458573572cc354c8564293f274801d9aa3e`. Padre comprobado:
`upstream/client_version/zone-10.0.2_r575`,
`7babcb3a706c64295b5aaaeec8abe57e4d09b4da`.

## Estado y alcance

**Reconstrucción parcial con correcciones verificadas; no aceptación retail completa.**
El usuario observa animación sin abanico al disparar al vacío y flechas dirigidas
a enemigos cuando existen. Flechas incesantes 14835/14836/14837 es la referencia
positiva aceptada por el usuario. Las capturas prueban el texto de la habilidad;
el comportamiento descrito por el usuario es evidencia separada.

Esta entrega corrige el transporte de objetivos, la multiplicidad de efectos,
el alcance del empuje y el presupuesto de eventos entre ramas. No demuestra por
sí sola que el cliente ya dibuje el abanico original. No se modificaron el
cliente, el `game_pak`, los datos de balance ni la base de datos de jugadores.
Se preservaron los 89 paths previamente modificados; los cambios previos del
ciclo de vida de proyectiles de Incesantes siguen presentes.

## Evidencia y procedencia

Raíz de evidencia fuera de Git:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archery-mist-repair-20260911`.
El análisis anterior está en la carpeta hermana `archery-analysis-20260911`.

| Fuente | SHA-256 / resultado |
|---|---|
| `data/sqlite/authoritative/game_decrypted.sqlite3` | `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f` |
| `x2game.dll` del cliente principal español | `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734` |
| Compact extraído del `game_pak` principal actual | `d3df9e18dad0775e5c2147e172a1a2256e54f173e099f4aa24700c90933524d4` |
| Comparación de la clausura full/compact efectivo | Cero diferencias en columnas operativas compartidas |
| Corpus release reanclado contra el PE principal | 16 funciones, todos los rangos de bytes idénticos |
| Base de conocimiento, dos generaciones independientes | `3768330a2e271d280bec80f8287efb0831a50afdb5c33e35950a16876291d1df` |

El hash del compact corresponde a una **extracción nueva del paquete**, además
de coincidir con el archivo suelto. No se atribuye al paquete completo ese hash.
El PE es x64, image base `0x39000000`; los localizadores siguientes son RVA.
Los archivos `.bytes`, `.c`, logs y `native-reanchor.json` conservan la cadena
desde el proyecto Ghidra de referencia hasta el binario principal modificado.

| RVA release | Contrato comprobado |
|---|---|
| `0xAB74D0` | Lector de SCPlotEvent: dos PlotObj; contador u8 y referencias Bc; flags y byte final de dirección |
| `0xAB3A40` | PlotObj type1: unidad; type2: posición/rotación, segunda posición/rotación y tres referencias |
| `0x33BE10` | Handler SCPlotEvent entrega los campos deserializados a PlayEvent |
| `0x6CE380` | PlayEvent aplica efectos fijos una vez y expande la lista solamente si source o target es selector4 |
| `0x6CDC70` | Resolución de selectores; target5 usa posición, sin unidad de destino |
| `0x6CCDD0` | SpecialType37 Projectile delega la creación al constructor nativo |
| `0x6CB250` | Constructor admite PlotObj type2 con coordenadas, sin enemigo; type1 sí exige unidad válida |

Zone r575 ofrece corroboración adicional de la multiplicidad, no sustitución de
la autoridad release. No se encontró en estos consumidores el scheduler World
que evalúa variables/tickets ni la semántica completa de RandomArea.

## Camino de la habilidad

El catálogo contiene 27 eventos; 21 son alcanzables desde 24561. Los históricos
24860–24864 y 25347 no son alcanzables y no deben activarse para inventar flechas.
No hay enlaces huérfanos en este grafo.

```text
24561 → 24564 (buff 21451, 2100 ms)
              ├→ 24563 (costes)
              └→ 51750 (arma)
                   ├→ 24562 (arco, tickets10, bucle200 ms)
                   │    └→ 24566 (cono30 m, máximo6, guarda targets en a)
                   │         ├→ por objetivo: 24567 (Projectile840) → daño → empuje
                   │         └→ 24570 (a<6)
                   └→ 51749 (arma de fuego, rama paralela nativa)

relleno: 24570 → 24565 (posición20 m delante)
              → 24854 (RandomArea, p3=6000,p4=8000; incrementa a)
              → 51754 (arma)
                   ├→ 51755 (Projectile1400 a posición)
                   └→ 24575 (Projectile840 a posición, NOT(a>5))
              → 24570
```

Projectile840 tiene la cadena de FX de flechas 2921 → 4627/4628. La selección de
unidades y el relleno a posiciones son dos rutas nativas distintas. Que algunas
flechas apunten a unidades **no demuestra por sí solo un homing artificial**;
la ausencia de relleno independiente de unidades sí requiere investigación.
El constructor nativo soporta ambas rutas. No se cambió el descriptor de arma.

## Correcciones de esta entrega

1. **Lista real de unidades en SCPlotEvent (`client-native`).** Antes se enviaba
   `target.UnitId` repetido tantas veces como resultados hubiera. Un ancla de
   posición producía una unidad cero. Ahora se envían las referencias reales de
   `EffectedTargets`, excluyendo 0 y MaxValue. Una posición conserva su PlotObj
   y lleva lista vacía si no hay unidades. SC, relay WZ y refresco de pesca
   conservan la misma lista. El lector no ignora todo efecto Location por una
   unidad cero: esa hipótesis inicial queda descartada como causa única.
2. **Multiplicidad de efectos (`client-native`).** Los selectores fijos se
   ejecutan una sola vez, con cero o muchos objetivos. El selector4 de fuente
   también itera cada unidad real. Se conserva el aislamiento de excepciones
   entre objetivos. Evita multiplicar contadores y efectos fijos por el número
   de enemigos encontrados.
3. **Range independiente del área (`server-required`).** La condición8619
   vuelve a evaluar 0..8 m. La búsqueda de 30 m ya no la ensancha. Se elimina la
   compensación transversal anterior de Backdraft; que un cono seleccione un
   candidato no garantiza que todos los efectos posteriores deban aplicarse.
   Se conserva el cálculo de distancia existente, incluida su política de
   radios de modelo: los tests aíslan distancias sin radio de modelo.
4. **Tickets por historial de rama (`server-required`).** Los hijos heredan el
   historial al bifurcarse; sus visitas posteriores no consumen tickets de sus
   hermanos. El bucle exterior10 puede volver a entrar al interior6 en cada
   salva. Los contadores globales de PlotState siguen siendo métricas, pero ya
   no son el límite compartido. Se conserva el gate existente para tickets0 y
   tickets1/self-loop. Esta es una representación interna necesaria para el
   grafo de AA10, no una afirmación de equivalencia binaria del scheduler World.

## Pruebas y límites

`AAEmu.UnitTests/Game/Models/Game/Skills/Plots/Fixtures/Neblina2957.json` conserva
las filas nativas de eventos, enlaces, condiciones y efectos. El extractor
comprueba igualdad contra el catálogo con hash fijado. El test usa PlotBuilder,
PlotTree, SetVariable, condiciones y el escritor SC reales; captura los bytes
sin red ni personaje persistente.

- Rama nativa de relleno desde24570, sin enemigos: emite eventos24575 POSITION.
  Esto es una prueba acotada; no incluye buff, costes, arco equipado ni el mundo
  real y **no prueba el número final de salvas de un casteo completo**.
- Presupuestos nativos10×6 disponibles al bifurcar; aislamiento de hermanos y
  continuidad del historial dentro de la misma rama.
- Wire con dos unidades distintas y con lista vacía; flags y dirección finales.
- Efecto fijo aplicado una vez con dos objetivos y con ninguno.
- Condición8619 a7,9/8/8,1/20 m tras una selección de30 m.
- Restore y build Release: correctos; build con263 advertencias, cero errores.
- Suite completa: **2765/2765**, incluye Incesantes, channeling y pesca.
- Base SQLite de conocimiento: `integrity_check=ok`, sin errores de claves
  foráneas y hash idéntico en dos generaciones.

**Pendientes concretos que impiden declarar reconstrucción completa:**

| Frontera | Evidencia actual | Trabajo necesario |
|---|---|---|
| Sexta flecha de relleno | El ejecutor real emite5; a llega a6 antes de NOT(a>5) | Cerrar orden/snapshot de variables del World nativo o captura equivalente; no cambiar la condición del catálogo por intuición |
| RandomArea p4 | AA10 contiene8000; el emulador lo suma como altura | AA8 propone corrección de terreno, pero falta consumer AA10; no se portó esa hipótesis |
| Daño cercano−20% | Texto y campos nativos de daño presentes | Reconstruir fórmula y ruta concreta, medir HP a ambos lados de8 m |
| Abanico visual y trayectoria | El binario acepta posiciones y el servidor las emite en la prueba | A/B en el cliente principal con la imagen desplegada |
| Cadencia completa | Grafo200 ms y buff2100 ms | Medir desde la entrada real, sin deducir duración de un test de tickets |

## Procedimiento reutilizable para otra habilidad

1. Separar petición del usuario, texto del tooltip y observación real. Usar una
   habilidad comparable aceptada como control, sin asumir que comparte el plot.
2. Resolver ID y todas sus variantes. Seguir skill→plot→eventos→enlaces→
   condiciones/efectos→buff/proyectil/FX. Conservar filas no alcanzables como
   evidencia negativa; no convertirlas en caminos activos.
3. Comparar full, compact retail, compact montado y entrada efectiva del paquete
   del cliente. Registrar hashes antes de atribuir el defecto al código.
4. Seguir el consumidor exacto: registro de packet→lector→handler→PlayEvent→
   selector→constructor de efecto. Reanclar bytes al binario actual por SHA,
   arquitectura y RVA. Un loader sólo demuestra carga, no ejecución.
5. Separar geometría de selección, condiciones de cada efecto, estado de
   variables, presupuesto de bucles, tiempo y transporte. Probar cero, uno y
   varios objetivos: estas rutas pueden ejecutar efectos diferentes.
6. Clasificar cada cambio como client-native, server-required o pendiente.
   AA8 es comparador. No rellenar huecos con IDs específicos, daño mágico,
   flechas sintéticas ni modificación del tooltip para ocultar un fallo.
7. Extraer un fixture fiel. Probar código real y bytes, además de regresiones
   de consumidores ajenos. Indicar qué contexto queda fuera del fixture.
8. Respaldar, desplegar y registrar hashes reales. La aceptación visual y de
   gameplay es un gate separado; una suite verde no la reemplaza.

Extractor reproducible:

```powershell
python reconstruccion_cliente_10/skills/archery_mist/audit.py --output <directorio-nuevo>
```

Genera `knowledge.sqlite3` con tablas source/entity/event/edge/finding y un
manifest. Consultas útiles: eventos no alcanzables, enlaces desde un evento y
`SELECT * FROM finding WHERE status IN ('open','pending')`.

## Despliegue, rollback y aceptación

Sólo se reemplaza el servicio `game` del proyecto Compose `aaemu10`, con los
archivos `docker-compose.yaml` y `.server_files/docker-compose.aa10.yaml`.
Respaldo: subcarpeta `rollback` de la evidencia. Imagen anterior etiquetada
`aaemu-world:before-neblina-20260911`; incluye dump consistente de aaemu_game/
aaemu_login, compact montado y hashes de DLL previas. El dump contiene datos
de jugadores y queda fuera de Git. No hubo migración ni cambio de compact.

Rollback de código: reetiquetar la imagen anterior con el tag del servicio y
recrear sólo `game` con `--no-deps --no-build`. No restaurar DB/compact para este
rollback si no hubo una modificación posterior que lo requiera.

La operación de Zones pertenece al usuario. Después del reemplazo de World,
comprobar el perfil en Control Center; Codex no inicia ni reinicia Zones.
Primera aceptación solicitada: equipado con arco, zona despejada y sin objetivo,
lanzar Neblina una vez. Registrar si aparece relleno durante todas las salvas.
Después probar enemigos dentro/fuera del cono y de8 m, repetición del casteo y
Flechas incesantes. Registrar por separado animación, flechas, daño, empuje,
duración y cooldown. No marcar estos resultados como PASS antes de observarlos.
