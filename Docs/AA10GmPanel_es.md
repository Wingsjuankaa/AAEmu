# Panel GM AA10

El icono circular **GM**, junto a Alpha privada y Reportar un error, abre el
catálogo de comandos que Game tiene registrados y que el personaje puede usar.
Se muestra únicamente cuando el servidor confirma acceso efectivo de nivel 50
o superior; cada operación vuelve a comprobar el permiso específico del comando.

## Uso

1. Abrir GM y buscar por comando, alias o descripción en español, o seleccionar
   una categoría. La búsqueda ignora tildes y mayúsculas.
2. Seleccionar un comando para consultar su descripción, sintaxis, alias y árbol
   de subcomandos. La ayuda del servidor conserva los tokens originales; puede
   contener inglés. Las páginas de ayuda evitan truncar árboles largos.
3. Escribir los parámetros sin `/comando`. Los botones `true`, `false` y
   `Ejemplo` rellenan el campo; no ejecutan. La línea inferior muestra el comando.
4. Pulsar Ejecutar y consultar el resultado en el chat. La confirmación de envío
   no se presenta como éxito de la mecánica: el comando original decide el resultado.

Favorito guarda el comando hasta salir o entrar en una pantalla de carga. Actualizar vuelve a leer el registro
actual y sus permisos. Los botones superiores ofrecen Sin CD, CD normal, Curar
(objetivo seleccionado) y Dummy (`/spawn npc dummy`). No conceden permisos nuevos.
El modo sin CD conserva GCD y tiempos de cadenas.

Acciones amplias o destructivas marcadas en el catálogo requieren un segundo clic
en Confirmar dentro de 20 segundos. Cambiar parámetros cancela la confirmación
del cliente; cambiar objetivo, perder permisos, expirar o reutilizarla impide
ejecutarla en el servidor. No hay reintentos automáticos de operaciones mutables.

## Implementación

- El registro de `CommandManager` es la autoridad de disponibilidad. No se
  mantienen comandos ejecutables independientes en Lua ni se eluden validaciones.
- `GmPanelDescriptions` contiene unidades editoriales es_ES por tipo concreto de
  implementación. Una prueba exige cobertura de todas las implementaciones actuales.
  Las nuevas reciben una descripción de reserva y confirmación; su metadata debe
  completarse para pasar la prueba de cobertura. Los alias no se duplican como filas.
- `SubCommandBase.DescribeTree` expone metadatos; nunca ejecuta una acción para
  descubrir su ayuda. No altera `PreExecute` ni el comportamiento del chat.
- Extensión `aa10gm1:` / `AA10GM1:` sobre el mismo transporte r575 de 48 bytes de
  nombre de canal que alpha/reportes. Fragmentos de 24 bytes, máximo 12, secuencia,
  caducidad y protección contra repetición de `AlphaTransport`, con sesión separada.
  El comando admite hasta 130 bytes UTF-8; rechaza controles, NUL y UTF-8 inválido.
- El servidor filtra permisos tanto en el catálogo como justo antes de despachar.
  El acceso efectivo incluye cuenta y personaje mediante `CharacterManager`.
  La UI exige emisor nativo `DAILY_MSG`, canal -2 y correlación de solicitud.
- No cambia cooldowns, skills, datos de personajes, SQLite ni configuraciones GM.

## Cliente y recurso gráfico

Target: `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`, canal interno `en_us`.
`components/module/module.alb` incorpora una clausura aislada que define el panel;
`hud/shortcut.alb` la inicializa después de cargar la biblioteca de widgets.
Se conservan las instrucciones, constantes y clausuras anteriores, incluido alpha.

El icono se generó con la herramienta integrada `image_gen`, usando el icono
alpha como referencia de estilo: medallón de bronce/dorado, centro verde azulado,
letras GM legibles y fondo transparente. Prompt y SHA están en
`Scripts/assets/gm-panel/icon.json`; la fuente PNG permanece versionada.
`BuildAa10GmIcon.py` convierte a BGRA8 DDS de 64×64 con siete niveles mip,
remuestreo premultiplicado y alpha conservado. La UI muestra 42×42 y cuatro estados.

## Instalación reproducible

`PatchAa10GmPanel.py` exige hashes exactos de fuente, compilador, ALB y extensión;
produce ALB del mismo tamaño y verifica preservación semántica. Los contratos
están en `Aa10GmPanel.contracts.json`. No regenerarlos durante la instalación.

`ApplyAa10GmPanel.py` hace dry-run por defecto. Primero ensaya ambos ALB y el DDS
en una copia dispersa del índice completo, verifica sentinelas de mapa, iconos,
crafting, alpha y reportes, y prueba el rollback. `--apply` exige cliente cerrado
y SHA completo final previamente fijado. Conserva offsets de todos los payloads
existentes; únicamente añade el DDS y reubica el índice con el mecanismo WIBO
ya usado por alpha. El crecimiento exacto y hashes están en el manifiesto.

Ante un fallo revierte el sufijo y los ALB en orden inverso, restaura metadata
original del índice y verifica el hash completo. Conserva respaldos por entrada,
índice y manifest bajo `E:/AAEmu/rama_10/backups/client-patches/aa10-gm-panel-*`.
Una segunda aplicación debe devolver `already_patched` sin modificar bytes.
No reaplicar antiguos parches alpha/layout sobre estos nuevos hashes: deben
conservar esta extensión o rechazar la identidad desconocida.

Control Center trata el SHA del paquete como informativo para su caché; no se
añade una allowlist. No se opera el cliente ni el lifecycle de Zones.

## Aceptación

La validación automática cubre permisos, sesión offline, revocación, replay,
confirmación de un solo uso, caducidad/cambio de objetivo, UTF-8, comandos inválidos,
metadata, interacción Lua y paquete. La suite verde no certifica el funcionamiento
de todas las mecánicas invocables: conserva las implementaciones existentes.

La aceptación visual/jugable queda a cargo del usuario: al entrar con un GM,
comprobar el icono transparente junto a alpha/reportes, abrir el panel, buscar
`ignorecd`, alternar su modo y usar Dummy. Con un jugador sin permisos el acceso
no debe mostrarse. Revisar acentos, recortes y ayuda paginada. No ejecutar acciones
globales para probar simplemente el panel.
