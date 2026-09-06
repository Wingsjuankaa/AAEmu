# Preparación rápida y progreso de parches — 2026-09-04

Target rama_10, HEAD bdad11fec1493c43a854369e707de72a20f26f86; padre upstream/client_version/zone-10.0.2_r575. Se actualizaron únicamente el editor local y su pipeline Python/JavaScript. No se operaron servicios AAEmu ni Zones.

## Comportamiento

Preparar verifica el SHA-256 del compact suelto conocido, valida revisiones y compara identidades semánticas. Produce un manifiesto formato 2 sin copias SQLite ni lectura de game_pak. La vista previa no certifica todavía la entrada incrustada. Aplicar verifica el hash completo del paquete, reextrae y valida la entrada efectiva, reproduce exactamente las diferencias revisadas, construye y valida la base y conserva el flujo de respaldo/escritura/reextracción/probes/hash final. Se rechazan revisiones posteriores o deriva de la fuente; se comprueba también la identidad del archivo tras construir, antes de escribir.

No se utiliza una caché basada solo en mtime para sustituir hashes. El ciclo pasa de tres a dos lecturas completas de 69.430.854.656 bytes. La construcción se desplaza a Aplicar; no se presenta ese desplazamiento como aceleración individual de la fase de aplicación. Cero diferencias no crea un respaldo ni escribe en el cliente.

El servicio publica progreso real por trabajo: etapas, duración y contadores de bytes/tablas. El frontend muestra historial y progreso de la etapa actual; no inventa porcentajes globales ni tiempos restantes. Recupera el trabajo activo tras recargar dentro de la misma sesión del servicio. Rechaza solicitudes simultáneas y bloquea su launcher durante el parche. El endpoint local autenticado de mantenimiento rechaza reiniciar con trabajos activos.

## Evidencia

- Preparación desde el servicio sobre el cliente instalado: 1,8 segundos, cero diferencias, 2.140 revisiones.
- Medición con el compact anterior verificado: 1,814 segundos, exactamente una diferencia y las mismas 2.140 revisiones. Reproducible con `scripts/benchmark_patch_preview.py --previous-patch 5f3fff53f81547d28993558f1fa6bd41`; resultados en `reports/preview-performance.json`. Se utiliza una copia previa como fixture; no se modifica el cliente ni se aprueban textos.
- Construcción y validación de la base r575 completa sobre la copia anterior: 13,622 segundos, una celda modificada, 1.003 tablas verificadas, SHA-256 resultante 934CB1A783691A9AE8B1545C452B006371BBA8F9B3A412025A7F5B704E063E4B, exactamente igual al instalado por el usuario. Informe `reports/preview-native-build-verification.json`.
- 32 pruebas Python correctas: preview sin lectura de paquete, aplicación/reversión en fixture aislado, compatibilidad de manifiestos previos, rechazo de paquete/preview/revisiones alterados, cero cambios sin escritura, exclusión de trabajos simultáneos y progreso de error, además de los controles lingüísticos anteriores. `node --check editor/app.js` correcto.
- Navegador: inicio de preparación, panel con etapa actual y duración, vista previa de cero cambios y botón Aplicar deshabilitado comprobados.

## Despliegue y límites

Editor reiniciado una vez concluido el parche del usuario; carga el código actualizado en 127.0.0.1:18775. Una segunda recarga del servicio se realizó usando la barrera de mantenimiento sin trabajos activos. Pestañas existentes requieren F5 después de conservar cualquier edición sin guardar.

No se aplicó un parche artificial al cliente para esta prueba. Su parche vigente sigue siendo 5f3fff53f81547d28993558f1fa6bd41: compact 934CB1A783691A9AE8B1545C452B006371BBA8F9B3A412025A7F5B704E063E4B; game_pak 42960F10D4C75F51CBB2F19ACDFDA3E55358502FACC6BB2AD804B8410B3ACE62. La siguiente edición real utilizará el aplicador con progreso. No se ha medido una duración nueva de escritura sobre el cliente real; las dos lecturas completas siguen siendo necesarias con este contrato.
