# Herramientas de alpha privada

Índice permanente: [Ventanas custom AA10](AA10CustomWindows_es.md).
Guía del formulario independiente: [Reportar un error](AA10BugReports_es.md).

Extensión personalizada para Returns 10.0.2.13 r575. No se presenta como una
mecánica retail. El cliente principal es `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.

Desde V10, el icono **α** junto a reportes, en la esquina inferior derecha,
abre la ventana para personajes autorizados. No exige llevar una llave.
La **Llave de alpha privada**, template `900001`, sigue siendo un acceso alternativo:
objeto ligado al personaje, no vendible y no consumible. Clic derecho en el bolso
abre la misma ventana de 760 × 720 con oro, labor, Honor, Vocación y catálogo paginado por nombre o ID. La búsqueda
acepta español, inglés e ID; incluye los ítems no subastables. Ignora mayúsculas
y tildes españolas, también en Docker con globalization invariant. Los nombres
mostrados corresponden al idioma del cliente.

Desde V8, escribir o borrar texto actualiza automáticamente los resultados tras
500 ms sin teclear. No es necesario pulsar Buscar ni Enter, aunque ambos siguen
disponibles. Se puede continuar escribiendo durante una consulta; se descartan
respuestas anteriores y se deshabilita Obtener hasta tener resultados vigentes.
Al vaciar el campo se consulta el catálogo completo desde la primera página.
Escribir nunca entrega objetos: Obtener sigue siendo una acción explícita.

El índice une el catálogo español con `ItemManager.searchString`, que contiene
el nombre original y todas las traducciones cargadas por LocalizationManager.
Por ejemplo, `Decorative Vase`, `Jarrón decorativo` y `98` encuentran el ítem 98.
Sólo se indexan nombres existentes; un objeto sin traducción inglesa o española
se puede localizar por ID o por otro nombre disponible.

La distribución restaura las 11.876 filas de `items` ausentes en la compact desde
la base AA10 completa: 51.010 ítems nativos más la llave. Los subtipos de esos
ítems ya estaban presentes. Conserva todas las filas originales, traducciones y
parches. Incluir un objeto histórico en el catálogo no reconstruye sus mecánicas
de uso ni prueba que sus habilidades estén implementadas.

## Acceso y uso

El acceso inicial solicitado corresponde a **Dannia**, character ID `1007`.
`private_alpha_access` persiste la autorización por personaje. Game entrega una
llave al terminar la entrada al mundo si el personaje está autorizado y no tiene
otra en sus contenedores. La entrega opcional requiere una ranura libre; un bolso
lleno o la llave guardada en el banco no impiden usar el icono.

Cada solicitud comprueba feature habilitada y autorización del personaje en el
servidor. No concede acceso GM. La revocación bloquea la siguiente operación de
una ventana ya abierta. El buscador no puede generar llaves adicionales.

El icono empieza oculto. Tras entrar al mundo, consulta el permiso a los 1,5 s y
lo vuelve a comprobar cada 30 s; si no recibe respuesta en 10 s, se oculta.
Los comandos GM online notifican el cambio inmediatamente. Los cambios mediante
el script SQL se reflejan en el icono durante la siguiente consulta; las operaciones
económicas validan siempre el permiso actual, independientemente del icono.

Concesión o revocación local, incluso con el personaje desconectado:

```powershell
.\Scripts\Set-PrivateAlphaAccess.ps1 -Character Dannia -Action Grant
.\Scripts\Set-PrivateAlphaAccess.ps1 -Character Dannia -Action Revoke
```

Con un administrador conectado también existe `/alphaaccess grant Dannia` y
`/alphaaccess revoke Dannia`; esta variante requiere al destinatario online y
intenta entregar la llave inmediatamente. La autorización se guarda aunque el
bolso esté lleno. Exige nivel administrativo 100 explícitamente.

Valores iniciales de `Configurations/PrivateAlpha.json`:

- Hasta 10.000 de oro por solicitud; unidad de UI oro = 10.000 cobres.
- Labor de cuenta hasta 5.000; no reduce saldos que ya superan ese límite.
- Desde V9, Honor y Vocación admiten enteros de 1 a 100.000 por entrega
  (límite fijo compartido por cliente y servidor). Añaden exactamente esa cantidad,
  sin bonificaciones de ganancia ni avance artificial de objetivos de misión.
  Se rechaza toda la operación si el saldo excedería `int.MaxValue`.
- Hasta 1.000 unidades de un ítem; grado 0–12, respetando el grado fijo y límites
  de la plantilla. Objetos sin grado conservan el suyo.
- Las entregas crean pilas nuevas y requieren las ranuras correspondientes.
  Mercancías que sólo admiten equiparse se rechazan sin entrega parcial.

El timeout de 20 segundos se mide con X2Time:GetUiMsec(), desde el instante de
cada solicitud, sin acumular el argumento de OnUpdate. No hay reintento
automático de una entrega. Ante timeout, comprobar inventario y
saldo antes de solicitar otra. Cada operación confirmada ya fue persistida.
Honor y Vocación se guardan en `characters.honor_point` y `vocation_point`
antes de actualizar memoria y notificar el saldo mediante los paquetes AA10
existentes. Su mutación comparte `GamePersistence.Sync` con los cambios normales
de puntos y el guardado general. No se añade una moneda ni un contrato de paquete.
La solicitud de un envío futuro por correo queda fuera de esta primera entrega.

## Contratos y seguridad

Acceso HUD V10: `Scripts/lua/PrivateAlphaShortcut.lua`, extensión aislada añadida
al ALB nativo `hud/shortcut`. Usa `ENTERED_WORLD`, `ENTERED_LOADING`, `LEFT_WORLD`
y `CHAT_MESSAGE`. El botón llama a `Aa10PrivateAlpha.Open()` después de confirmar
el permiso. La consulta `access` es de sólo lectura, con límite independiente de
5 segundos; no afecta al límite de las operaciones económicas.

Entrada alternativa: `bagInjector:PreUseSlot`, consumida por el callback nativo `PreUse` de
`inventory/sort_inventory.lua`. Sólo intercepta el template custom y devuelve
`true` para impedir uso/venta/traslado incidental mediante ese clic.

Transporte custom: `X2Chat:JoinUserChatChannel`, names reservados `aa10ap1:`;
reutiliza el límite r575 demostrado por Ipnya (48 bytes, password vacío, create
false). Hasta 12 fragmentos ASCII de 24 caracteres, ensamblado ordenado, TTL de
5 segundos, máximo 10.000 IDs por sesión y deduplicación durante toda la sesión.
No crea canales ni ejecuta comandos GM recibidos del cliente.

Las respuestas usan `SCChatMessagePacket`, canal System **-2**, sin remitente
en el paquete y prefijo `AA10AP1:`. El dispatcher r575 transforma ese remitente
en **DAILY_MSG** antes de emitir `CHAT_MESSAGE`. La UI exige canal -2, remitente
DAILY_MSG y el ID pendiente. V7 corrige el filtro vacío que descartaba respuestas
válidas y mantenía los controles apagados. El protocolo sigue visible en el chat
de sistema; se comprobó su recepción dentro del cliente real.

Oro y labor persisten antes de modificar caché o publicar resultados. Los ítems
se preparan sin añadirlos al bolso; una transacción SQL guarda las nuevas pilas
y, al autorizar, el acceso. Sólo después del commit se añaden mediante el
lifecycle normal de inventario y se publican tareas. Un fallo previo al commit
libera los IDs preparados sin emitir adquisición ni paquetes.

El API administrativo existente continúa sólo en el puerto interno 1280. Este
trabajo no publica puertos ni opera el lifecycle de las Zones.

## Construcción y despliegue

V10 usa `BuildAa10AlphaIcon.py`, `PatchAa10AlphaShortcut.py` y
`ApplyAa10AlphaShortcut.py` (dry-run por defecto; `--apply` instala).
El aplicador exige la identidad exacta del paquete, ensaya sobre un archivo
disperso con el índice completo, prueba rollback y reextrae mapa/icono/Folio,
alpha V9 y reportes V4. Conserva todas las instrucciones nativas del HUD,
añade una clausura Lua y empaqueta `game/ui/custom/aaemu/private_alpha.dds`
como BGRA8 con 7 mipmaps. No usa una textura loose ni modifica la compact.
El icono fuente, metadatos y conversor están en `Scripts/assets/private-alpha/`.
El respaldo contiene la entrada original y las colas exactas original,
intermedia y final del paquete. La reversión devuelve primero el índice y
después el ALB con `PakEntryReplace`; restaura su metadata original sólo tras
comprobar que ningún otro registro cambió.

La instalación V10 y sus hashes están registrados en
`reconstruccion_cliente_10/checkpoints/CHECKPOINT_PRIVATE_ALPHA_HUD_20260912.md`.
Su aceptación visual dentro del juego queda pendiente de la prueba del usuario.

`PatchAa10PrivateAlpha.py` valida hashes exactos de fuente, ALB, compact,
compilador y base nativa. Compila Lua 5.1 x64 con cabecera r575. La compact se
compacta con VACUUM y se extiende con páginas libres registradas en la freelist
de SQLite hasta el tamaño exacto original, conservando schema_version=1006.
Se exige igualdad entre tamaño físico y page_count × page_size, además de
integrity_check y preservación de todas las filas previas. El relleno con ceros
de V1 era inválido para el cliente nativo aunque Python SQLite lo aceptaba.
V3 reconoce los hashes V1/V2 únicamente como entradas de reparación. El r575
rechaza también freelists con más de (usableSize / 4 - 8) hojas por trunk;
se reservan los seis slots finales por compatibilidad nativa. Referencia:
https://sqlite.org/fileformat.html#the_freelist. La prueba real de V2 detectó
ese segundo rechazo aunque SQLite moderno aceptaba la estructura.

`ApplyAa10PrivateAlpha.py` es dry-run por defecto; `--apply` aplica dos entradas
con respaldo, rollback inverso, reextracción y sentinelas de mapa/icono/Folio.
Sincroniza la compact loose y emite `manifest.json` con hashes completos del
paquete. No requiere ni añade una allowlist al Control Center: la caché actual
se invalida por ruta/tamaño/mtime.

El builder genera `private_alpha_catalog.json` desde los nombres efectivos del
cliente. Copiarlo a `.server_files/AAEmu.Game/Data/` y copiar la configuración
versionada a `.server_files/AAEmu.Game/Configurations/` antes de recrear Game.
Aplicar `SQL/updates/2026-09-11_aaemu_game_private_alpha.sql` a `aaemu_game`.

Rollback: usar la imagen previa registrada en el manifiesto de despliegue,
restaurar las entradas del cliente mediante sus respaldos y hashes parcheados,
restaurar la compact loose y deshabilitar/revocar accesos. No restaurar una DB
entera sobre avances posteriores para eliminar una sola autorización.

## Aceptación dentro del cliente

V7 se probó con Dannia el 2026-09-11: primera apertura autorizada, controles
habilitados, catálogo de 51.010 resultados, paginación, búsqueda «Jarrón» e ID
98, resultado vacío, entrega de 1 oro y 1 Jarrón decorativo. Se rechazaron cantidad
0 y una entrega de 21 objetos con sólo 20 ranuras libres, sin entrega parcial.
Revocar acceso con la ventana abierta bloqueó la siguiente operación; después
se restauró la autorización original exclusivamente de Dannia.

La solicitud de labor se rechazó correctamente: la cuenta ya tenía 9.380,
por encima del límite configurado de 5.000. La entrega positiva de labor queda
sin prueba nativa; no se redujo el saldo para forzarla. También quedan sin prueba
nativa otro personaje sin acceso, entrega rápida repetida y variaciones de grado.
Las pruebas automatizadas no sustituyen esos casos pendientes.

Evidencia y persistencia tras relog: `CHECKPOINT_PRIVATE_ALPHA_20260911.md` y
`PRIVATE_ALPHA_20260911.manifest.json` en `reconstruccion_cliente_10/checkpoints`.
La Zone Gatekeeper Hall ya estaba saludable y se conservó sin reiniciarla.

V9 añade Honor y Vocación. La instalación, hashes, rollback y pruebas automatizadas
se registran en `CHECKPOINT_PRIVATE_ALPHA_POINTS_20260911.md` y
`PRIVATE_ALPHA_POINTS_20260911.manifest.json`. La aceptación de los nuevos
controles queda pendiente de prueba del usuario; éste retomó el control de Zones
y pruebas. Probar primero +1 Honor, correlacionar saldo/UI/SQL, luego +1 Vocación,
rechazo de 0 y persistencia al volver a entrar. No se han concedido puntos como
parte del despliegue.
