# Checkpoint V2: corpus transparente de código nativo AA8

Fecha de cierre: 2026-07-30

Cliente fijado: Kakao `8.0.3.12 r558734`

## Resultado

La infraestructura del plan integral quedó implementada y ejecutada sobre el
cliente real. El resultado es un corpus lateral reproducible y navegable; no es
una reconstrucción del C++ original ni un cliente recompilable.

El pseudocódigo, las instrucciones y los resultados por motor permanecen en:

`E:\AAEmu-Research\output\aa8-native-code\stage-15-native-code.sqlite`

El grafo consolidado incorpora sólo artefactos, evidencia, cobertura,
validaciones y regiones opacas:

`E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite`

No se modificó AAEmu, `.env`, MySQL, compact runtime ni Docker del servidor. No
se analizó, ejecutó ni instrumentó anticheat.

## Entradas congeladas

- 204 fuentes PE detectadas.
- 202 binarios únicos y 2 aliases.
- 53 binarios propios habilitados para análisis.
- 146 dependencias externas inventariadas solamente.
- 3 componentes de anticheat excluidos antes de programar motores.
- Inventario SHA-256:
  `E10928C73CD694BC481391D7CFC42728CE808601E5356408688E4DA8F6A36D0A`.
- Configuración SHA-256:
  `CF0F642B4411C72686140A3DBD3066BB22BEBB5B6904719E6E0B24EC33F333B1`.
- 50 funciones ancla: 25 x86 y 25 x64.
- Anclas SHA-256:
  `5C680BA429399E485B563E2336AA1CD1767FB87FF76A403EB40608BD37DD7CC3`.
- PDB x64 preservado como evidencia:
  `D:\work\x2.autobuild\trunk\dev64\x2game.pdb`,
  GUID `DF3CE336CE3F4D55B064E97D110A6753`, age `1`.
- La ausencia de PDB local también queda registrada como evidencia negativa.

## Stage 15 final

- Tamaño: `7.953.125.376` bytes.
- SHA-256:
  `E8479BCFBFAF48D45A053A9A2D3048D0E253009DA0B9E491E26D2608174073F0`.
- 19 manifiestos crudos de motor incorporados.
- 202 binarios.
- 189.142 funciones.
- 9.314.237 instrucciones con RVA, mnemonic, texto y bytes.
- 1.603.970 bloques básicos.
- 554.790 llamadas.
- 530.039 referencias de datos.
- 919.006 resultados o estados explícitos de decompilación.
- 278.672 nombres con procedencia.
- 50.892 strings y 75.618 asociaciones función/string.
- 2.665 tipos y 5.390 campos.
- 1.964 vtables y 174.063 slots.
- 3.368 equivalencias x86/x64:
  22 `confirmed`, 3.304 `corroborated` y 42 `candidate`.
- 184.640 entradas en la cola de revisión, incluyendo estados de motores
  fallidos o no programados.
- 346.684 regiones ejecutables:
  186.858 funciones, 802 thunks, 130.880 paddings y 28.144 regiones opacas.
- 2.343 campos candidatos inferidos desde accesos `this + offset`.
- 1.358 nombres nativos confirmados desde exports.
- 60 enlaces desde consumidores/anclas forenses.

Validación final:

- `PRAGMA quick_check = ok`.
- `PRAGMA integrity_check = ok`.
- 0 violaciones de claves foráneas.
- 0 secciones ejecutables con partición incompleta.
- 0 resultados obligatorios ausentes.
- 0 ejecuciones de motor sobre anticheat.
- 0 trazas dinámicas inválidas.

Dos construcciones consecutivas desde el mismo conjunto de 18 entradas
produjeron exactamente:

`DBA6F995F6113305156A677069158637696AACD823B54002E70846FBF5E45BFD`

Después de esa prueba llegó el manifiesto final de rev.ng x64. La última
construcción, con 19 entradas, cambió legítimamente al SHA final indicado
arriba.

## Cobertura real de motores

### `x2game.dll`

- Ghidra 12.1.2: cobertura completa x86/x64, lotes deterministas de 500.
- Rizin: cobertura completa x86/x64.
- angr: 50 anclas, indirect calls y metadatos de bloqueo.
- Reko x86: completado y normalizado.
- Reko x64: sigue ejecutándose dentro del timeout de módulo de 12 horas. Hasta
  que publique manifiesto, la matriz conserva `not_scheduled`.
- rev.ng x86: `failed`, exit `245`, crash reproducible en `Lift Pass`.
- rev.ng x64: `failed`, exit `247`; sin salida C.

Los fallos de rev.ng son evidencia explícita y no se interpretan como ausencia
de función. Cada función conserva una fila de estado por motor requerido.

### Código propio adicional

- `xlcommon.dll` x86/x64: Ghidra y Rizin completos.
- `archeage.exe` x86/x64: Ghidra y Rizin completos.
- Los otros 47 binarios propios habilitados permanecen `not_scheduled` hasta
  ejecutar la fase de ampliación. Su inventario, imports, exports, secciones y
  regiones opacas ya son consultables.

Las primeras salidas Ghidra, anteriores al exportador con instrucciones, se
movieron de forma recuperable a:

`E:\AAEmu-Research\output\aa8-native-code\archive\ghidra-pre-instructions`

Los temporales incompletos creados durante una detección de doble constructor
fueron eliminados después de verificar que ningún proceso los utilizaba. No se
eliminaron salidas crudas ni corpus válidos.

## Consolidado final

- Tamaño: `8.448.872.448` bytes.
- SHA-256:
  `FE5F0235BE2E520F1BDF8F4714FF8AE8A2545E39ED8937D02DBEE01FC0B44C87`.
- 10 stages en linaje, incluyendo Stage 15.
- 928 artefactos.
- 28.282 regiones opacas.
- `quick_check = ok`.
- `integrity_check = ok`.
- 0 relaciones, propiedades, resultados cached, wiki o work queue huérfanos
  en la validación independiente.

## Visor y exportación

El servidor se limita por política a `127.0.0.1`. Smoke test sobre el corpus
final:

- `/`: HTTP 200 en ~7 ms.
- búsqueda `rva:005eaf50`: HTTP 200 en ~0,89 s.
- búsqueda FTS `DOODAD_PHASE_MSG`: HTTP 200 en ~4 ms.
- detalle de función: HTTP 200 en ~0,23 s.

La función de ejemplo se exportó como dossier autocontenido:

`E:\AAEmu-Research\output\aa8-native-code\dossiers\x2game.dll-x64-005eaf50.html`

El nombre del dossier incluye módulo, arquitectura y RVA para impedir
sobrescrituras entre funciones.

## Pruebas

- 55 pruebas unitarias/doradas.
- Cobertura de PE32/PE32+, VA/RVA, identidad estable frente a ASLR, exclusión
  de anticheat, FTS, red dinámica pública rechazada, nombres multi-procedencia
  sin duplicar equivalencias y dossiers únicos por arquitectura/RVA.
- Compilación Python completa sin errores.
- `git diff --check` sin errores de whitespace.

## Siguientes pasos

1. Dejar terminar Reko x64. Si publica manifiesto, ejecutar
   `build-stage-15`, `validate-stage-15` y `consolidate`.
2. Procesar los 47 binarios propios restantes, primero módulos XL/X2 y Cry de
   gameplay/red/scripts/entidades; usar Ghidra y Rizin obligatoriamente.
3. Priorizar las 28.144 regiones opacas y la cola de revisión por consumidores
   confirmados, indirect calls, límites discordantes y tipos incompatibles.
4. Revisar las 42 equivalencias candidatas; no propagar sus nombres hasta
   confirmación.
5. Ejecutar evidencia dinámica sólo después del corpus estático: copia
   separada, offline/local, anticheat ausente, escenarios pequeños y hashes de
   traza. Actualmente hay 0 ejecuciones dinámicas registradas.

## Comandos operativos

```powershell
python -B -m client_forensics inventory-native-code
python -B -m client_forensics select-native-anchors
python -B -m client_forensics run-native-decompiler --engine ghidra --binary x2game.dll --architecture x64 --scope full --resume
python -B -m client_forensics build-stage-15
python -B -m client_forensics validate-stage-15
python -B -m client_forensics diff-native-architectures
python -B -m client_forensics serve-native-code --bind 127.0.0.1 --port 8765
python -B -m client_forensics export-native-function x2game.dll 0x5EAF50 --architecture x64
```

`run-all` valida y consume Stage 15, pero no vuelve a ejecutar motores. Una
regeneración costosa requiere `run-all --refresh-native-code`.
