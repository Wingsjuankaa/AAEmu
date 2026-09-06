# Intercambio de traducciones del taller · 2026-09-04

Target: `E:/AAEmu/rama_10/localization/aa10-es-es`. Contexto del servidor: `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`, padre contrastado `upstream/client_version/zone-10.0.2_r575` en `3cc280b14d7da0d874121d14ebbf409f5e032d1c`. Se preservaron los cambios previos. No se operaron Zones, servidor AAEmu ni cliente del juego.

## Contrato

`contextual_exchange.py` implementa archivo JSON UTF-8 `aa10-editor-translations`, versión 1, build `10.0.2.13-r575`, locale `es_ES`, checksum SHA-256 canónico de entradas. Identidad completa tabla/columna/idx y hash de fuentes exactas; cada entrada comparte inglés, español, estado y notas. Exporta revisiones contextuales guardadas, incluidas las instaladas. Por defecto filtra procedencia del editor (manual o importada); opciones para aprobadas y todas las revisiones contextuales. No exporta el corpus base masivo, SQLite, rutas de configuración, capturas, credenciales, modelos ni game_pak. Las notas de usuario se comparten como texto.

Importación en dos fases: vista previa persistida y selección explícita con huella de la revisión local. Rechaza versión/hash inválidos, duplicados, identidades ausentes, fuente distinta y texto estructuralmente incompatible. Iguales se omiten; conflictos se dejan desmarcados; incompatibles son inseleccionables. El estado predeterminado es draft (blocked se conserva); preservar estados, incluidas aprobaciones, requiere elegir ese modo. No realiza aprobaciones por traducción automática ni modifica el cliente.

Carga cada selección como revisiones con historial y procedencia de importación. Revalida la selección completa antes de escribir. Journal con estado anterior, overlays y nombres del historial permite revertir fallos del lote; el arranque recupera imports interrumpidos antes de conciliar el índice. Repetir el mismo lote completado devuelve cero. Fuentes modificadas tras la vista previa invalidan la carga. Límite 10 MB/10.000 entradas. Operaciones autenticadas y serializadas con el parche y barrera de mantenimiento. Editor único por catálogo; no compartir una carpeta viva entre procesos.

## Verificación y despliegue

- 45 pruebas Python correctas (37 previas + 8 de intercambio): roundtrip entre dos catálogos aislados, borrador por defecto, aprobación explícita, selección parcial de conflictos, idempotencia, obsolescencia sin escritura parcial, identidad/fuentes/hash/tokens incompatibles, rollback de archivos/historial/FTS e interrupción recuperada al reiniciar.
- JavaScript comprobado con `node --check`.
- Datos reales: 11 correcciones, 7.120 bytes, exportación 0,167 s; 10 aprobadas, 6.734 bytes; todas las revisiones contextuales: 2.149, 838.561 bytes, exportación 0,175 s y preview 1,812 s. Medidas puntuales, no garantías de latencia.
- Autoimportación en vista previa: las 11 correcciones coinciden; las 2.149 revisiones arrojan 2.147 iguales y 2 incompatibles preexistentes, que no se cargan ni se corrigen en esta tarea.
- Navegador real: descarga desde Exportar; chooser de Importar; 11 iguales con carga deshabilitada; fixture de conflicto de nota con casilla inicialmente desmarcada, seleccionable y botón habilitado solo después de selección. Fixture cancelado sin guardar. Sin errores de consola.
- API viva: export/preview/import con selección vacía retorna cero; digest del conjunto editorial idéntico antes/después.
- Servicio del editor reiniciado mediante `/api/drain` sin trabajos activos y launcher `Iniciar editor.ps1 -NoBrowser`. HTTP en 127.0.0.1:18775. Pestañas anteriores necesitan F5 después de guardar ediciones abiertas.

Evidencias: `reports/exchange-v1/verification.json`, `reports/exchange-v1/live-api.json`; archivos exportados de ejemplo en esa carpeta. Manifest con hashes en `manifests/translation-exchange-v1.json`. Instrucciones de uso en `editor/README.md`. Para ver traducciones recibidas en el juego sigue siendo necesario aprobar, preparar y aplicar el parche. La portabilidad del editor completo sigue pendiente.
