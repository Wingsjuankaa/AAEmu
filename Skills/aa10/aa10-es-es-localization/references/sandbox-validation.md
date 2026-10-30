# Validar español en el sandbox

Laboratorio aceptado: E:\AAEmu\rama_10\runtime\sandbox-aa10. El acceso
Iniciar sandbox AA10.cmd entra automáticamente con Sandbox aZone411
aa10_sandbox_lab. Usa cliente español privado con +locale en_us, cuatro
dummies y NPCs de especializaciones, banco, armas y armaduras.

Pedir al usuario una prueba concreta en su cliente; conserva el control del
escritorio. Para iniciar/reparar runtime o aplicar C# usar la skill de
reconstrucción, su referencia mechanics-sandbox.md y la autorización actual.
No iniciar ni cerrar otras Zones por validar un texto.

- El cliente principal español continúa como distribución mantenida. La copia
  sandbox conserva parches propios de entrada/perfil/escena: no copiarle un pak
  entero ni reemplazar DLLs desde el principal, porque perdería esos cambios.
- Mantener las unidades traducidas como fuente, builder/aplicador, hashes,
  respaldo por entrada y reextracción. Un parche privado de QA no se considera
  entregado al principal ni traducido globalmente por funcionar en el sandbox.
- El panel de carga propio evita pantallas negras; no ocultar ni mover el
  renderer del juego. El lobby privado debe nombrar aa10_sandbox_lab.
- Hot Reload aplica C# compatible al servidor real. Lua/ALB, compact, iconos,
  modelos y game_pak necesitan su pipeline y la recarga/reapertura apropiada;
  no prometer actualización de esos assets por dotnet watch.
- No modificar números mecánicos para corregir un tooltip:23592 ya anunciaba
  correctamente45 m; el fallo estaba en geometría del servidor y se reparó allí.

Guías del repo E:\AAEmu\rama_10\server\AAEmu:
Docs/AA10SandboxSeparateZone_es.md, AA10SandboxHotReload_es.md,
AA10PrecisionShotRange_es.md y AA10SandboxProfile_es.md. Capturas y temporales
nuevos en E. Mantener acentos, terminología y trazabilidad igual que en el principal.
