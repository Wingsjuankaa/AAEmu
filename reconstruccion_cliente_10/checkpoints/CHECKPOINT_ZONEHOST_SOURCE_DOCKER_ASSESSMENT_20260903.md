# ZoneHost: fuente integrada y evaluación Docker

Estado: incorporación de fuente y evaluación estática completas. La petición posterior
del usuario habilitó publicación automática de Release y Control Center 0.1.6;
el candidato fue publicado el 2026-09-03 a las 23:13:21 UTC con respaldo exacto.
Aceptación de gameplay y contenedor pendientes como pruebas separadas.

- Source of truth: `Tools/AAEmu.ZoneHost`, snapshot comunitario `8801e8272309b53288b63c4869a83f01b42eae14`.
- Fuente original conservada con licencia, manifiesto UTF-8/LF y 32 archivos.
- Rust fijado, MSVC/SDK registrados, build offline; no dependencia nueva del servidor .NET.
- Release CRT estático, 306.176 bytes, SHA256 `1A2F91A758E08D2597ED8A6DC8C23B4C65A6C69A2EDE782DA4D9A5E2079F1E03`.
- Dos builds con igual hash; tres probes de argumentos y seis checks PE correctos.
- Restore/build Release del servidor y 1.756 tests correctos en la ejecución registrada.
- Docker actual Linux: no soporta este host/DLL como proceso nativo Linux.
- Receta experimental Windows preparada; imagen y carga de Zone no probadas.
- Wine sigue siendo hipótesis, no una ruta validada ni una solución demostrada de RAM.
- La primera entrega conservó el host instalado. La actualización posterior lo
  reemplazó atómicamente al estar libre y añadió consumo de pendientes al panel;
  no se operaron Zones. Ver cronología y respaldo en el informe.

Informe y procedimiento: [AA10ZoneHostSourceIntegration_es.md](../../Docs/AA10ZoneHostSourceIntegration_es.md).
