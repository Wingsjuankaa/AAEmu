# Guia para repetir la Fase 1 con otras especializaciones

## Proposito

Este documento convierte el trabajo realizado con Battlerage en un proceso
repetible. Debe utilizarse para catalogar Shadowplay y las especializaciones
posteriores sin mezclar datos 8.0 con definiciones historicas ni inferir
estructuras del cliente.

La Fase 1 es de investigacion y catalogacion. No modifica el runtime, las
compact originales, MySQL, Docker ni personajes.

## Estado de la implementacion actual

El extractor actual esta orientado a Battlerage, aunque ya acepta
`--ability-id`. Antes de utilizarlo para otra especializacion deben
parametrizarse tambien:

- nombre de la especializacion;
- habilidad simple usada como ancla manual;
- habilidad compleja usada como corte vertical;
- nombre de los archivos de salida;
- validaciones especificas que hoy exigen los IDs y cantidades de Battlerage.

No se debe cambiar solamente `--ability-id` y considerar el resultado
terminado: el encabezado, las pruebas doradas y la seleccion vertical seguirian
siendo de Battlerage.

## Fuentes de verdad

Usar siempre este orden de autoridad:

1. `compact-client-8.0-decrypted.sqlite`, como vista de datos del cliente.
2. `game11`, para resultados de consultas que no quedaron materializados en
   la SQLite de investigacion.
3. `x2game.dll`, para confirmar SQL, orden de columnas y tipo de cada lectura.
4. Trafico y comportamiento observado con el cliente 8.0 local.
5. Compact 3.0 y rama `develop`, solo como referencia de implementacion o como
   evidencia cruzada explicitamente registrada.
6. Wiki de la epoca, solo para validar el comportamiento visible.

Rutas utilizadas en Battlerage:

```text
D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite
E:\AAEmu-Research\output\compact-8.0-extracted\game11
E:\AAEmu-Research\input\x2game.dll
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-loot-hybrid.sqlite3
D:\Proyectos\AAemu\client_kakao\compact.sqlite3
E:\AAEmu-Research\output\ghidra-static
```

Los hashes concretos se registran dentro de los JSON generados. Nunca debe
reutilizarse un resultado si el hash de una fuente cambio sin volver a ejecutar
las validaciones.

## Cadena que debe reconstruirse

Para cada habilidad o pasiva se debe poder recorrer y atribuir:

```text
specialization
  -> skill / passive_buff
  -> skill_effect
  -> effect
  -> concrete effect
  -> buff template, si corresponde
  -> buff relations, tags y condiciones
  -> clase y loader existentes en AAEmu
```

Cada nodo debe indicar si procede de cliente 8.0, `game11`, runtime hibrido o
referencia historica. La existencia de un ID igual en 3.0 no demuestra que sus
campos tengan el mismo significado en 8.0.

## Procedimiento completo

### 1. Congelar las entradas

- Registrar ruta, tamano y SHA-256 de las tres compact y de `game11`.
- Confirmar rama y commit del codigo.
- Abrir todas las SQLite con `mode=ro` y `PRAGMA query_only = ON`.
- No reemplazar la compact usada por Docker durante esta fase.

### 2. Identificar la especializacion

- Confirmar su `ability_id` en datos 8.0.
- Enumerar todas las filas `skills` asociadas.
- Separar habilidades visibles, variantes internas y ancestrales.
- Enumerar sus `passive_buffs` desde el resultado nativo de `game11`.
- No asumir que `skills.ability_id` define por si solo la pantalla de
  aprendizaje; esa seleccion pertenece al nucleo de especializaciones de la
  Fase 2.

### 3. Recuperar relaciones nativas

- Filtrar el resultado completo `skill_effects` recuperado desde `game11` por
  los IDs de la especializacion.
- Resolver `effects.actual_type` solamente mediante evidencia estable.
- Recuperar la fila del efecto concreto segun el tipo resuelto.
- Recorrer todos los `BuffEffect` hasta su `buff_id` y sus relaciones.
- Conservar por separado cualquier relacion historica utilizada solo como
  comparacion.

### 4. Recuperar una tabla nueva desde `game11`

Cuando una tabla necesaria aun no tenga extractor:

1. Buscar en `x2game.dll` la consulta exacta `SELECT ... FROM tabla`.
2. Convertir el offset PE de la cadena a direccion virtual usando las
   secciones del binario; no sumar offsets de forma manual sin verificar la
   seccion.
3. Ejecutar `DecompileStringReferences.java` contra esa direccion.
4. Identificar la funcion loader y todas las lecturas de columna.
5. Registrar el layout exacto por indice. En este cliente se confirmaron:

   | Accesor virtual | Tipo serializado |
   |---|---|
   | `+0x38` | booleano de 1 byte |
   | `+0x60` | `double` de 8 bytes |
   | `+0x68` | entero de 32 bits |
   | `+0x40` o `+0x70` | entero de 64 bits |
   | `+0x78` | string inline o referencia |

6. Elegir un ancla conocida que produzca una sola coincidencia valida.
7. Exigir filas consecutivas iniciadas por `SQLITE_ROW` y cierre exacto con
   `SQLITE_DONE`.
8. Registrar bytes inicial/final, cantidad de filas, ancla, funcion Ghidra y
   layout en `result_ranges`.
9. Agregar una prueba dorada con campos estables del ancla.

No se acepta un layout solo porque genera valores plausibles. Debe coincidir
con todas las llamadas de acceso por columna del loader de `x2game.dll`.

### 5. Resolver strings referenciados sin inferir

Los strings de `game11` pueden aparecer como `<ref:N>`.

- Usar directamente `localized_texts` cuando exista nombre o descripcion
  inglesa para el mismo `tbl_name + idx`.
- Para strings tecnicos, construir evidencia con filas compartidas cuyo ID y
  restantes campos relevantes sean identicos.
- Resolver una referencia solo si todos los pares compartidos apuntan a un
  unico valor historico.
- Si existen candidatos distintos o no hay evidencia, conservar `<ref:N>` y
  marcarlo como no resuelto.

Ejemplos confirmados:

- `effects.actual_type` se resuelve por `effect.id + actual_id` estable.
- `<ref:69859>` de `buff_unit_modifiers.owner_type` se resuelve como `Buff`
  mediante 46 filas compartidas estables.
- `<ref:69871>` sigue sin resolverse; no afecta el corte de Battlerage y no se
  le asigno un significado supuesto.

### 6. Tratar correctamente las relaciones de buff

Las cuatro tablas nativas recuperadas son:

- `buff_tick_effects`;
- `buff_triggers`;
- `buff_unit_modifiers`;
- `tagged_buffs`.

En `buff_unit_modifiers`, un buff puede aparecer como objetivo en `buff_id` o
como propietario en `owner_id` cuando `owner_type` se resolvio como `Buff`.
Buscar solamente por `buff_id` omite relaciones validas.

### 7. Construir cobertura de backend

Para cada tipo alcanzado:

- confirmar la fila concreta 8.0;
- localizar la clase bajo `AAEmu.Game/Models/Game/Skills/Effects`;
- confirmar que `SkillManager` registra su loader;
- contar relaciones nativas y filas concretas encontradas;
- marcar explicitamente datos faltantes o tipos no implementados.

`backend_present_native_source_confirmed` significa que la relacion nativa, el
efecto concreto y, para `BuffEffect`, la plantilla `buffs` 8.0 fueron
recuperados. No significa por si solo que la mecanica ya se haya probado dentro
del juego.

### 8. Elegir dos validaciones manuales

Seleccionar:

- una habilidad simple, con una cadena corta que permita detectar rapidamente
  errores del extractor;
- una habilidad compleja o visible, con varios tipos de efecto, para validar el
  recorrido completo.

Para ambas, una consulta SQL independiente debe devolver los mismos IDs que el
manifiesto. Para la compleja se debe exigir que no existan efectos concretos ni
buffs nativos faltantes.

### 9. Generar y verificar resultados

Ejecucion actual de Battlerage:

```powershell
python .\extract_battlerage_manifest.py `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --client-game-stream E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-loot-hybrid.sqlite3 `
  --server-reference D:\Proyectos\AAemu\client_kakao\compact.sqlite3 `
  --source-root D:\Proyectos\AAemu\rama_8 `
  --output .\generated `
  --verify
```

Para la siguiente especializacion se debe usar una salida independiente, por
ejemplo:

```text
generated/shadowplay/
```

No sobrescribir el manifiesto Battlerage durante la comparacion.

Ejecutar el extractor dos veces y comparar SHA-256 de todos los entregables.
Los hashes deben ser identicos.

## Checklist de cierre por especializacion

- [ ] `ability_id` y nombre confirmados.
- [ ] Activas, variantes y pasivas enumeradas.
- [ ] Relaciones `skill_effects` nativas recuperadas.
- [ ] Todos los `actual_type` resueltos o marcados como no resueltos.
- [ ] Cada relacion nativa encuentra su efecto concreto 8.0.
- [ ] Cada `BuffEffect` encuentra plantilla y relaciones nativas.
- [ ] Clases y loaders de AAEmu inventariados.
- [ ] Habilidad simple validada por consulta independiente.
- [ ] Habilidad compleja validada de extremo a extremo.
- [ ] Procedencia historica separada de la fuente 8.0.
- [ ] Dos ejecuciones producen hashes identicos.
- [ ] Informe de resultados y siguiente bloqueo documentados.
- [ ] No se modificaron compact originales, runtime, MySQL ni personajes.

## Orden correcto despues de Battlerage

La reconstruccion de datos de Battlerage cerro la Fase 1, pero antes de aplicar
el mismo proceso a Shadowplay debe completarse la Fase 2 del plan:

1. estabilizar seleccion y cambio de especializacion;
2. confirmar experiencia, niveles, puntos y requisitos;
3. corregir aprendizaje, reinicio, guardado y carga;
4. validar barras de accion y dos relogs consecutivos;
5. impedir que una habilidad invalida corrompa la transaccion del personaje.

Con ese nucleo estable, Shadowplay es la siguiente especializacion recomendada
porque ya expuso fallos de activacion y persistencia. Su catalogo debe generarse
en una carpeta separada reutilizando esta guia, no copiando las definiciones de
Battlerage ni de la compact 3.0.

## Referencias del trabajo Battlerage

- `extract_battlerage_manifest.py`: extractor reproducible.
- `FASE_1_RESULTADOS.md`: resultados, cantidades y validacion Battlerage.
- `PLAN_RECONSTRUCCION_SKILLS_AA8.md`: orden general de fases.
- `generated/battlerage-skill-manifest.json`: evidencia completa por habilidad.
- `generated/effect-coverage.json`: cobertura de clases y loaders.
- `E:\AAEmu-Research\output\ghidra-static\buffs-loader.c`: loader de `buffs`.
- `E:\AAEmu-Research\output\ghidra-static\buff-relations-loaders.c`: loaders de
  relaciones de buff.

