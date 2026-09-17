# Invocación de barcos en orillas y lagos — 2026-09-16

## Problema y corrección

Los intentos de Dannia en Solzreed a las 22:28–22:29 UTC rechazaban Moby Drake
(slave 578, modelo 1834, ship_model 36) aunque hubiera agua suficiente. El servidor
exigía `mass_box_size_z - mass_center_z + 1 = 10 - (-3,3) + 1 = 14,3 m`.
Esos datos describen la distribución de masa de la física, no el volumen del casco.
El arreglo anterior amplió el alcance desde la orilla, conservando ese error.

Ahora se cargan `slaves.obb_pos_*` y `obb_size_*` del catálogo AA10. La parte inferior
del volumen de Moby es `2,659173 - 8,816892 / 2 = -1,749273 m` respecto al origen.
Se comprueba que el fondo quede por debajo de ese volumen al invocarlo en la
superficie del agua. No se cambia la flotación, el empuje ni el simulador de Zone.
En modo Game standalone se tiene en cuenta una sola vez su desplazamiento vertical
de plantado ya existente; ZoneAuthority no lo aplica.

También se sustituye el vecino de navegación `.bai` por el mapa de alturas XY,
interpolado por World. El vecino de navegación podía estar en otra posición y
no representar el fondo situado debajo del barco. El chequeo incluye los bordes
y el interior de la caja, en una cuadrícula de separación máxima de 2 m, con
su centro desplazado y el giro final del barco (jugador + 90 grados). Si el centro
cabe pero la popa toca la orilla, la búsqueda continúa con otra posición.

La comprobación se aplica a los barcos con geometría válida del catálogo, no es
una excepción por ID de Moby. El runtime contiene 122 de 131 templates de clases
de barco con caja positiva; los otros nueve conservan la validación anterior.

## Evidencia nativa

Binario AA10 x64 `zones/retail-zone-server-r575/Bin64/x2game-dev_dedicate.dll`,
SHA-256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`.
Base de imagen `0x39000000`.

- RVA `0xB002E0`: loader de `slaves`, campos de centro y dimensiones de la caja.
- RVA `0x737F80`, `X2::GameClient::SlaveLocator::GetSpawnPosition`: construye
  explícitamente `centro ± tamaño * 0,5` desde offsets `0x38–0x4C` del descriptor.
  El float de RVA `0xF8CDD4` vale exactamente 0,5. Si falta caja, crea un modelo
  temporal para obtenerla; ese fallback de modelo no se reconstruye aquí.
- RVA `0x736FC0`: búsqueda nativa; consulta terreno y superficie de agua,
  realiza pruebas físicas y entrega la posición/orientación.
- RVA `0x736E40`: prepara centro y semiextensiones de la caja para colisiones.

Este cambio cierra la interpretación de la geometría y corrige el gate de terreno
del servidor. **No reproduce todavía toda la consulta nativa de colisiones con
objetos**, ni sustituye la búsqueda angular existente por el algoritmo nativo.
No se presenta el muestreo del heightmap como colisión exacta de CryPhysics.

Evidencia durable fuera de Git:
`E:/AAEmu/rama_10/artifacts/ship-summon-lake-20260916/`:
decompilados `server-obb-all.log`, `server-boat-placement-native.log`,
`server-boat-clearance-native.log`, logs de reproducción, extracción read-only
del heightmap de celda 013_014 y script de consulta. El heightmap corrobora
aproximadamente 7,5–10,1 m en los puntos de nado reportados. El SQL runtime
confirma las seis coordenadas/dimensiones de Moby; no se modifica SQLite.

## Validación y despliegue

Restore y build Release: correctos, cero errores. 12 pruebas nuevas y suite
completa: **4.631 correctas**, cero fallos u omitidas. Cubren el lago observado,
orilla/nado, profundidad insuficiente, datos ausentes/no finitos, popa sobre tierra,
orientación, continuación de búsqueda y fallback sin caja.

Game/World desplegado a las **22:52:55 UTC**. Imagen
`sha256:5ac7c26bae371e626aaa6dbc7fbc9f72cd92be243698382bfa6f7e69c836ec81`.
DLL Game en `/app/` y `/app/game/`:
`01752a132d6adc474e52ad18e17d1c2d1a7b2c9c2cdbce04d2410bc473ff93bf`.

Se fijó el ensamblado portable de la salida de pruebas compilada a las 22:50:05
UTC y se construyó una imagen sobre la imagen desplegada anterior. Había ediciones
simultáneas posteriores en ItemManager/LootingContainer; no se incorporaron a esta
entrega ni se sobrescribieron. Commons, dependencias y World no cambiaron en esta
corrección. Dockerfile y binarios exactos quedan en `artifacts/.../deploy/`.

Rollback: etiqueta `aaemu-world:rollback-ship-summon-lake-20260916` y respaldo
MySQL/compact en `backups/ship-summon-lake-20260916/`. Cliente y Zones no modificados;
su lifecycle sigue bajo Control Center y el usuario.

**Aceptación pendiente:** después de levantar las Zones desde Control Center,
invocar una vez Moby Drake en el mismo lago. Los logs deben indicar
`requiredDepth=1.75`, `nativeBounds=True`, posición en superficie, y el barco
debe aparecer y permanecer estable. Después comprobar desde la orilla y con el
pesquero normal. No declarar esos resultados observados antes de la prueba.
