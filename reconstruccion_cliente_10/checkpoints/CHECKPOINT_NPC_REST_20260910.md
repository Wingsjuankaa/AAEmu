# Cierre de NPC restantes — 2026-09-10

Alcance: 14308 nombres de npcs/name del grupo 03. Revisión directa en este chat,
60 lotes, sin modelos externos ni subagentes. 0 candidatos sin examinar.
10979 aprobados instalados, 2993 excluidos con evidencia,
336 fuentes sin resolver que permanecen sin aprobar.
106 correcciones finales; auditoría sin errores.

Cliente operativo: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
Parche `67f349be0b644e9aa90cb643491cd552`, aplicado 2026-09-10T11:40:16.642412+00:00; 7130 cambios efectivos.
Reextraído y verificado el compact del paquete; 16149 nombres aprobados exactos,
incluidos los 5170 previamente instalados. 0 pendientes globales.
1003 tablas y 11 recursos verificados.
Segunda aplicación: already-applied; tamaño y mtime del paquete intactos.

game_pak antes: `F97247362A65DB3BA316AE46656F8FD2CBFB1AADB360AE2E36265084133DA56A`.
game_pak después: `EEF02413603E9DE85205CD8EE11D3845FA45A9BDCF76430A15D0297EF06A4E40`.
Tamaño antes: 86302933504 bytes. Después: 86772732928 bytes.
Crecimiento: 469799424 bytes por el aplicador vigente PakEntryRelocate.
Compact antes: `7AE0AEBFBF83EB73C0B8339741BD6493F96F7230C32DC2770DB834B0FA094483`.
Compact después: `827D17C9FC7A31C40B32AD834F9CE1B52D80EF8DC3D80046D28D9784F6219856`.
Rollback por entrada: `E:\AAEmu\rama_10\backups\client-patches\contextual-67f349be0b644e9aa90cb643491cd552`. Sin copia integral del paquete.

Builder/aplicador existente: localization/aa10-es-es/scripts/contextual_patch.py
y PakEntryExtract de la rama 10 más tools/PakEntryRelocate del editor.
El aplicador permite relocalizar la entrada al crecer, exige hash previo exacto
y reabre/reextrae para verificar tamaño y SHA-256. Solo cambia
localized_texts.en_us de las identidades seleccionadas; ninguna tabla mecánica.
Orquestación reproducible: work/close_npc_rest.py; decisiones y QA de cada lote
referenciadas con SHA-256 en reports/npc-rest-20260910/review-evidence.json.
Política: decisions/0021-npc-rest-20260910.md.
Manifiesto: reports/npc-rest-20260910/package-manifest.json.
Inventario: reports/npc-inventory-20260909/README.md.
Informe completo: reports/npc-rest-20260910/README.md.

Panel: typecheck, 65 pruebas (1 omitida), 20 archivos y build correctos.
GamePakSource/MapAssetService invalidan por ruta/tamaño/mtime; hash informativo.
No se cambió código del producto, el cliente original ni los servidores.
Motor del editor iniciado en 127.0.0.1:18775 para guardar y aplicar.

Prueba retail pendiente del usuario: comprobar un NPC genérico traducido y uno
con nombre propio conservado, un interlocutor de misiones previamente aplicado,
un mapa y un icono de objeto; comprobar navegación normal y ausencia de cambios
mecánicos. No se afirma aceptación visual ni se realiza commit/push.
Alias y diálogos fuera de este alcance. No se reabren excepciones previas.
