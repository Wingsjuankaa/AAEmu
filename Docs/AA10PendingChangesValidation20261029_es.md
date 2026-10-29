# Validación de cambios propios antes de integrar el padre — 2026-10-29

Target: `Wingsjuankaa/AAEmu:rama_10`, repositorio canónico
`E:/AAEmu/rama_10/server/AAEmu`. HEAD inicial
`1c724fccc84580ba975233b3419b4deb939b6b24`, idéntico a `origin/rama_10`.
Padre exacto: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`, corte
`78533663d9ca93dc4aa610c088359312f91f4293`.

## Cambios preservados

- Playit: puerto Stream anunciado opcional, fallback al listener para LAN,
  pruebas del paquete para autoridad normal/GM, helpers históricos y runbook.
- Perfil local: admite exclusivamente los dos manifiestos conocidos del
  launcher 0.2.2 y conserva las entradas de launcher al aplicar/revertir la DLL.
- Habilidades: autoriza los hijos de Bola de fuego después del disparo real;
  aplica el selector nativo de `skill_reqs` y las exenciones de Defiance,
  conservando los anclajes SHA-256/RVA, pruebas y scripts forenses.

El estado inicial incluye 13 archivos modificados y 8 nuevos. Respaldo previo
a cualquier edición: `artifacts/pre-upstream-validation-20261029/`, fuera de Git,
con el diff binario y copias de los archivos nuevos. SHA-256 del diff:
`6311E499AEED7C64EF8D3EDD89FED6499BFEFD7B46CA56983EB5B32C7F4F147E`.

## Validación actual

- `dotnet restore`: correcto.
- `dotnet build --configuration Release --no-restore`: 0 errores; 29 advertencias
  en los proyectos de integración (xUnit1051, xUnit2031 y CA2000).
- `dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore`:
  **5664 correctas, 0 fallidas, 0 omitidas**.
- `python Scripts/tests/test_local_profile.py -v`: **10 correctas**. Las pruebas
  preparan el instalador desde el código actual del repositorio, sin usar una
  copia empaquetada anterior. Incluyen ejecución de la DLL nativa en sandbox,
  Apply/Rollback, repetición, conservación byte a byte de ambos manifiestos
  0.2.2, rechazo de modificaciones desconocidas y recuperación ante error.
- Ambos scripts PowerShell pendientes pasan el parser.
- El helper Playit pasa una ejecución aislada de `powershell.exe -File` desde
  otro directorio, preservación de perfil LAN y fecha de creación, repetición,
  respaldos y rechazo de schema desconocido sin mutación. En esa prueba solo
  se redirige la consulta de ApplicationData al sandbox; no se escribe el
  perfil real ni se abre el launcher.
- `git diff --check`: correcto.

Las pruebas de instalador requieren Windows y los binarios r575 exactos
disponibles en el cliente canónico; los binarios no se incluyen en Git.
El fixture del manifiesto contiene solo metadatos/hashes de la entrega.

## Límites y continuación

Estos cambios ya tenían despliegues registrados en los checkpoints de septiembre.
Esta validación no vuelve a desplegar ni certifica una sesión retail nueva.
Las pruebas de interacción de Bola de fuego/Defiance y de otro PC siguen pendientes.
Docker no estaba disponible durante la revisión inicial; no se han operado Zones.

La publicación debe preceder a la integración del padre. La localización
`localization/aa10-es-es` tiene un Git separado, sin commits ni remoto; esta
publicación del servidor no incorpora automáticamente ese corpus.
