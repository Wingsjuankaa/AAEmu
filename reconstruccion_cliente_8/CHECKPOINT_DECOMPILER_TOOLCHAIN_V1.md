# Checkpoint de toolchain de decompilación AA8 V1

Fecha de auditoría: `2026-07-30`.

Cliente objetivo: Kakao `8.0.3.12 r558734`.

## Objetivo

El objetivo no es sustituir una revisión binaria manual por pseudocódigo no
verificado. Es producir una representación de alto nivel, local, consultable y
reproducible del cliente, donde cada función conserve su dirección, hash,
arquitectura, evidencia y desacuerdos entre motores.

La unidad de trabajo pasa a ser:

```text
función nativa
-> límites y llamadas normalizadas
-> pseudocódigo de varios motores
-> tipos/clases recuperados
-> evidencia dinámica opcional
-> índice SQLite y vista estática
```

La decompilación nunca recupera el código fuente original de forma exacta.
Nombres, tipos, macros, comentarios y construcciones C++ perdidas deben
reconstruirse con evidencia. El pseudocódigo por sí solo no es autoridad para
layouts, fórmulas o protocolo.

## Hallazgo principal

La instalación existente ya tenía Ghidra `12.1.2`, PyGhidra, x64dbg, Procmon,
ProcDump y unluac. El hueco no era otro depurador interactivo: faltaban motores
de decompilación independientes y una forma reproducible de comparar sus
salidas.

El catálogo V1 añade:

- Reko `0.12.4`, publicado el `2026-07-29`;
- Cutter `2.5.0` y Rizin `0.9.1`;
- angr `9.3.1.post1`, publicado el `2026-07-29`;
- rev.ng fijado por digest OCI;
- RetDec `5.0` como voto antiguo pero independiente;
- CERT Kaiju `260608`, compatible con Ghidra `12.1.2`;
- PE-bear `0.7.2`, capa `9.4.0` y FLOSS `3.1.1`;
- DynamoRIO, Frida y WinDbg TTD como rutas dinámicas aisladas;
- Binary Ninja Free e IDA Free como opciones manuales, con sus límites de
  licencia, automatización y privacidad.

La fuente máquina legible es:

```text
config/decompiler-tools.json
```

El instalador reproducible es:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\tools\sync_decompiler_toolchain.ps1 -Profile core
```

Perfiles:

- `core`: decompiladores y triage estático local;
- `extended`: suma motores antiguos, cobertura e instrumentación;
- `all`: todo lo instalable sin pasos de licencia manual;
- `verify`: no descarga; comprueba la instalación actual.

Los archivos grandes permanecen en `E:\AAEmu-Research`. El repositorio sólo
conserva catálogo, scripts y checkpoints. Cada descarga con digest publicado se
verifica antes de extraerla. Para releases antiguas sin digest publicado se
registra el SHA-256 observado en el manifiesto local, sin presentarlo como
digest del editor.

## Prioridad técnica

### 1. Corpus base

Ghidra sigue siendo la base porque conserva el trabajo ya realizado y permite
automatización headless. Debe exportarse un corpus completo por función con:

- arquitectura, image base, VA/RVA y bytes;
- hash de bytes y hash normalizado;
- nombre nativo o reconstruido y estado del nombre;
- llamadas, referencias de datos, strings y vtable/RTTI;
- prototipo, calling convention y tipos aplicados;
- pseudocódigo y errores del decompilador;
- versión de herramienta y hash del binario.

### 2. Votos independientes

Reko, angr, rev.ng y RetDec deben ejecutarse sobre la misma función o cierre.
Un consenso mejora la legibilidad, pero no convierte una inferencia compartida
en evidencia nativa. Los desacuerdos son resultados positivos: señalan límites
de función, indirect calls, stack frames o tipos que requieren revisión.

### 3. Recuperación C++

Kaiju/OOAnalyzer, RTTI, vtables y constructores deben producir tipos aplicables
a Ghidra. El objetivo es reemplazar expresiones como `*(param_1 + 0x38)` por un
campo con identidad y procedencia, no inventar nombres cómodos.

### 4. Priorización por ejecución

DynamoRIO/drcov, Frida o WinDbg TTD sólo se usan sobre la ruta local aislada y
sin Easy Anti-Cheat. La cobertura se mapea a VA/RVA y al corpus estático. No se
instrumenta un servicio o cliente de terceros ni se comparte memoria capturada.

## Criterio para dejar la exploración binaria ad hoc

Se alcanza cuando el corpus:

1. cubre todas las funciones descubiertas de `x2game.dll` x86 y x64;
2. conserva una salida o un error explícito por motor;
3. permite búsqueda por nombre, dirección, ID, string, tabla, packet, vtable y
   caller/callee;
4. enlaza cada afirmación al binario y versión exactos;
5. registra regiones opacas y funciones no decompilables;
6. se reconstruye dos veces con hashes idénticos;
7. alimenta el grafo forense sin sustituir su política de autoridad.

Hasta entonces, el binario sigue siendo la autoridad, pero deja de ser la
interfaz cotidiana.

## Riesgos y descartes

- Binary Ninja Cloud e IDA Free cloud no deben recibir el cliente completo.
- BinDiff/BinExport queda en espera: el release actual tiene reportes de
  incompatibilidad con Ghidra 12 y se probará primero en un proyecto
  desechable.
- RetDec es útil como voto, pero su último release estable es de 2022.
- Instrumentación dinámica puede fallar o ser bloqueada por el anticheat; no se
  usa para el flujo normal de producción.
- Ningún decompilador devuelve el C++ original ni prueba layouts por sí solo.

## Validación ejecutada

Se verificó la instalación completa de los perfiles `core` y `extended`.
Quedaron operativos Ghidra, Reko, Cutter, Rizin, angr, Kaiju, PE-bear, capa,
FLOSS, rev.ng, DynamoRIO, Frida, x64dbg, Procmon, ProcDump y unluac.

El smoke test usó el launcher AA8 nativo:

```text
E:\AAEmu-Research\input\archeage.exe
sha256=2b967212c3f5265e566168688e6f6ad79190f8b972cfc1566d316a4403645f32
```

Resultados:

- Reko generó `archeage.h`, globals, asm, disassembly y
  `archeage_text.c` de `35.283` bytes. Produjo pseudocódigo útil, pero también
  dos errores internos de tipos; deben conservarse como desacuerdos del motor.
- angr recuperó `217` funciones, decompiló el entry point y produjo tipos como
  `STARTUPINFOW`; registró calling conventions desconocidas y dejó deshabilitado
  su backend opcional Unicorn, sin impedir la decompilación estática.
- rev.ng recuperó `99` funciones en una salida PTML/C de `1.380.066` bytes y
  aplicó `Microsoft_x86_64` con estructuras de stack inferidas.
- Rizin confirmó para `x2game.dll` PE32+ AMD64, MSVC, seis secciones, la ruta
  original `D:\work\x2.autobuild\trunk\dev64\x2game.pdb` y GUID
  `DF3CE336CE3F4D55B064E97D110A67531`.
- RetDec se extrajo y verificó por SHA-256 local, pero el ejecutable Windows no
  inicia sin `libcrypto-1_1-x64.dll`. No se copió una DLL arbitraria de otro
  producto ni se instaló un runtime OpenSSL 1.1 retirado. Queda catalogado como
  bloqueado hasta aislarlo en Linux/WSL o construir un contenedor reproducible.

Salidas locales:

```text
E:\AAEmu-Research\output\decompiler-toolchain\installed-tools.json
E:\AAEmu-Research\output\decompiler-toolchain\smoke\reko-archeage
E:\AAEmu-Research\output\decompiler-toolchain\smoke\revng-archeage
```

## Próximo checkpoint

`V2` debe implementar el exportador de corpus multi-motor, validar un conjunto
de funciones ancla ya confirmadas y cargar resultados en una nueva etapa
forense sin alterar las bases actuales.
