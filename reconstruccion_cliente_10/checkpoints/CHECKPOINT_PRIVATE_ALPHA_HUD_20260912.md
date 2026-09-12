# Alpha privada V10: acceso desde HUD

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre
`upstream/client_version/zone-10.0.2_r575`.

## Comportamiento

Icono circular α, a la izquierda del icono de reportes, con tooltip «Alpha privada».
Sólo aparece tras confirmar autorización desde Game. Abre la misma ventana V9:
oro, labor, Honor, Vocación y catálogo ES/EN/ID. La llave 900001 queda como atajo
opcional; no se exige en el bolso ni para abrir ni para ejecutar operaciones.
Dannia/1007 sigue siendo la única autorización de la DB. No se modificaron filas,
saldos ni inventarios para esta prueba.

El HUD consulta `access` 1,5 s después de `ENTERED_WORLD`, después cada 30 s;
oculta el botón ante denegación, cambio de mundo o timeout de 10 s. El servidor
limita la consulta de sólo lectura a 5 s, separada del límite económico de 350 ms.
Los comandos administrativos online emiten `access` con ID 0. Un script SQL se
refleja durante la siguiente consulta. Cada operación comprueba el permiso actual;
una ventana abierta no permite saltarse una revocación. El canal System -2 /
DAILY_MSG es el transporte previamente demostrado; sus mensajes técnicos siguen
visibles en el chat de sistema, incluida la consulta periódica de permiso.

## Evidencia y frontera cliente

- `hud/shortcut.lua` nativo usa `ENTERED_WORLD`: carrier cargado durante HUD.
- Se conserva el bytecode nativo, constantes y funciones; se quita debug y se
  añade una clausura aislada. No se recompila la lógica nativa.
- Carrier `game/scriptsbin64/x2ui/hud/shortcut.alb`, 24.447 bytes.
- ALB previo `46BCF5A6F056B0CE0E716D3154FE6CE337183D15DEAB47A87D864E49F614B934`.
- ALB nuevo `381535536C48588063509F14CA19B90B52B5DB887C41CD7B3CB09F3B84BE557E`.
- Recurso nuevo `game/ui/custom/aaemu/private_alpha.dds`: 21.972 bytes,
  BGRA8, 64×64, 7 mipmaps, alfa real. SHA
  `90B6EAF0601AC2B820D2F0CE385865AC1334AA0BEB4BF77D3BDC23567C6FE3B6`.
- Arte fuente: `Scripts/assets/private-alpha/alpha-icon-source.png`, generado
  con image_gen; prompt y procedencia en `icon.json`. Conversión compartida con
  el icono de reportes V3 aceptado. Cuatro estados mediante tintes y desplazamiento.
- El DDS se añade al final de los payloads, conservando offsets y registros de
  todas las entradas existentes. Única excepción: metadata del ALB del HUD que
  `PakEntryReplace` actualiza al sustituirlo por otro del mismo tamaño.
- Ensayo sobre archivo disperso con todos los registros reales y los payloads
  afectados/sentinelas. Reextracción por AAPak y rollback exacto del índice pasaron.
- No se modifica compact, alpha V9, reportes V4, DDS de reportes, mapa o Folio.

## Identidades

Cliente principal `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.

| Artefacto | Antes | Después |
|---|---|---|
| game_pak bytes | 92412619776 | 92412641792 |
| game_pak SHA-256 | `EF979561B7B28087E25DC24704BEF5BC2F4C99E3D631433CC7D360A61C6D4B34` | `B70AA4AA707E188BA8736D9770F542109377446EABFCA8142A7517B811FC8C22` |
| Game imagen | `sha256:c5d9e2d7e66849f87bce95b68d1d4af263346b6d60ad16ae918f45e5a54c261d` | `sha256:308afd63c409a3c5cbfefd565fbf7b3d481d05b114cf793056240bc9dc8da3f7` |
| Game DLL | `E467AC30D16CB7AC1682D07A83C6EE3D478F957BE5FA1284A7C899B5BE426634` | `92AEAECEB68C10530A0164D3787F566DEDB181B0E664C62E04ED54EE26A0DAA5` |

## Validación

- Restore y build Release: 0 errores; 2.777 pruebas unitarias pasadas.
- Lua: 3 pruebas de acceso HUD, 9 de alpha V9 y 9 de reportes V4.
- Paquete: 2 pruebas de composición/reversión y 4 de append/DDS.
- Integración read-only `Tools/AlphaAccessProbe`, sobre DB real: Dannia
  autorizado sin construir inventario, otro personaje denegado, feature global
  deshabilitada denegada. Cero mutaciones SQL.
- Control Center: typecheck, 65 tests pasados / 1 omitido y electron-vite build.
  Caché inspeccionada: ruta/tamaño/mtime; SHA informativo, sin allowlist cerrada.
- Desplegado y reextraído en el cliente principal. Segunda ejecución: `already_patched`,
  SHA completo sin cambios. Game healthy, 0 reinicios; DLL raíz y `/app/game`
  coinciden. Startup confirmado en 1239/1240/1250. Manifiesto hermano
  `PRIVATE_ALPHA_HUD_20260912.manifest.json` incluye respaldos y pruebas.
- Aceptación visual/funcional V10: **pendiente del usuario**, no operada mediante
  automatización. La aceptación anterior del icono de reportes no sustituye ésta.

## Prueba dentro del cliente

El usuario conserva el control de las Zones. Entrar con Dannia y esperar la
confirmación de permiso; debe aparecer α junto a reportes. Pulsarlo: la ventana
existente debe abrir y habilitarse. Comprobar hover/tooltip/clic y que el icono de
reportes y el HUD nativo sigan funcionando. La llave debe seguir abriendo la misma
ventana. Con la llave en banco, el icono mantiene el acceso. Un personaje sin
autorización no debe ver α. La prueba de revocación se coordina antes de mutar
la autorización; el rechazo servidor ya se verificó mediante el probe read-only.

## Rollback

Imagen retenida como `aaemu-world:rollback-alpha-hud-20260912`. Restaurar sólo
Game con esa identidad si es necesario; no operar Zones. El backup del aplicador
conserva ALB, índice original, índice intermedio y cola final. La función
`rollback` del aplicador revierte primero el append, después el ALB mediante
`PakEntryReplace` y finalmente su metadata exacta, rechazando cambios ajenos.
Verificar SHA previo completo antes de aceptar una reversión. No restaurar DB
ni compact: no cambiaron en esta entrega.

Guía permanente: [AA10PrivateAlpha_es.md](../../Docs/AA10PrivateAlpha_es.md).
