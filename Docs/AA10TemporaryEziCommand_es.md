# Zona temporal de Ezi — comando GM

`/ezi 300` crea un área fija de 50 m de radio en la posición mundial actual del personaje durante cinco minutos. `/ezi 300 100` elige 100 m de radio. `/ezi 0` retira la zona creada por ese GM en la instancia actual.

La duración admite enteros entre 1 y 86400 segundos; el radio, entre 5 y 500 m. Solo existe una zona por creador e instancia: repetir el comando reemplaza su ubicación y plazo. Acceso GM 100 por la política predeterminada de CommandManager/AccessLevelManager. No se habilita para jugadores normales.

Dentro del área, los barcos vivos reciben Protección divina de Ezi (13816) y Amarrado/Moored (13817), que permite personalizar componentes y recuperar salud. El centro permanece fijo al desplazarse el GM. Se usa la posición mundial, también cuando el personaje está sobre un barco. La distancia es tridimensional. El efecto se actualiza en el tick de 500 ms: salir, cancelar o alcanzar el plazo lo retira en el siguiente tick. La zona sirve a los barcos presentes y a los que entren o se invoquen después.

Es una herramienta GM solicitada por el usuario, usando los buffs del catálogo AA10 y su transporte habitual a la Zone. No crea geometría ni un círculo nuevo en el mapa del cliente. No es una zona general de invulnerabilidad o protección PvP para personajes.

## Evidencia y aislamiento

Catálogo autoritativo AA10 SHA-256 `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f`: sphere2307 → SphereBuff5 → buff13817, con retirada al salir; sphere2312/2313 → SphereBuff10/11 → buff13816, sin retirada declarada en el puerto original. Ambos buffs tienen slave_applicable=true. El texto nativo de 13817 especifica personalización de componentes y regeneración del barco.

La duración y radio de la herramienta son parámetros GM pedidos por el usuario, no una modificación del balance de estos buffs. El consumidor temporal lleva propiedad por instancia exacta de Buff: retira únicamente lo que añadió, notifica por índice a la Zone y conserva buffs preexistentes o reemplazados por otra fuente. Si un puerto normal pasa a suministrar el buff, cede su propiedad al puerto, respetando la semántica original de Ezi. Las zonas superpuestas mantienen los efectos mientras alguna cubra el barco. Vehículos terrestres y otras instancias quedan fuera.

La geometría temporal solo vive en memoria. El ciclo de vida del mundo elimina las áreas y sus efectos; un reinicio no las restaura. No cambia SQLite, game_pak, ZoneHost, archivos de spawns ni las áreas originales. Se preservan los cambios de impuestos/grupo de la otra tarea ya presentes en el runtime.

## Validación

Build Release y 4610 pruebas correctas, sin fallos ni omisiones. Siete pruebas nuevas cubren entrada, frontera, plazo exacto, repetición, salida/reentrada, superposición, reemplazo y cancelación por creador, efectos ajenos, transferencia al puerto natural, limpieza, aislamiento de instancia, exclusión de vehículos y rechazo sin mutación. La retirada se comprueba con notificación a Zone habilitada.

Evidencia de datos, logs y respaldo: `E:/AAEmu/rama_10/artifacts/ezi-area-20260916`. Detalles de entrega en `AA10TemporaryEziCommand.manifest.json`. Aceptación visual en el cliente pendiente; no se operó el ciclo de vida de Zones.

Desplegado el 16/09/2026 a las 14:50:11 UTC, imagen `sha256:63166f4afdc9fc02937774c31c2975d28952002f639bb7667c956d6f65a66fb3`. Game, Stream y MainWorld listos, Web API responde y cero reinicios. El archivo de comando dentro del contenedor coincide por SHA-256 con el fuente. Rollback: `aaemu-world:rollback-ezi-20260916`.
