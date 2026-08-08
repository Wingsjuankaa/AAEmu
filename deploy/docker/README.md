# Despliegue Docker de AAEmu

Este despliegue genera tres imágenes publicables:

- `wingsjuanka/aaemu-database:<tag>`
- `wingsjuanka/aaemu-login:<tag>`
- `wingsjuanka/aaemu-game:<tag>`

La base de datos, los logs y los activos grandes no se guardan dentro de las
imágenes. MySQL usa un volumen persistente; `game_pak` y `compact.sqlite3` se
montan desde el servidor de destino en modo de solo lectura.

En una instalación nueva, la imagen de base de datos crea ambos esquemas,
carga la Marketplace base e instala el catálogo DEV preparado en este fork.

## Preparación

Desde la raíz del repositorio:

```powershell
Copy-Item .env.docker.example .env.docker
```

Edita `.env.docker` y reemplaza las contraseñas, rutas y endpoints públicos.
En el servidor de destino, la ruta indicada por `AAEMU_CLIENT_DATA_PATH` debe
contener `game_pak`. `AAEMU_COMPACT_PATH` debe apuntar al archivo
`compact.sqlite3`.

## Construir y publicar

Estas órdenes descargan las imágenes base únicamente cuando decidas ejecutarlas:

```powershell
docker compose --env-file .env.docker -f compose.production.yaml build
docker compose --env-file .env.docker -f compose.production.yaml push
```

## Arrancar en el servidor de destino

Con las imágenes ya publicadas:

```bash
docker compose --env-file .env.docker -f compose.production.yaml pull
docker compose --env-file .env.docker -f compose.production.yaml up -d --no-build
docker compose --env-file .env.docker -f compose.production.yaml ps
```

Adminer es opcional y sólo queda publicado en `127.0.0.1`:

```bash
docker compose --env-file .env.docker -f compose.production.yaml --profile tools up -d adminer
```

## Migrar el estado actual

Las imágenes nunca deben contener personajes, cuentas ni contraseñas. Para
mover el estado existente, genera un `mysqldump` completo de `aaemu_login` y
`aaemu_game`, cópialo al nuevo servidor y configura `AAEMU_DB_RESTORE_PATH`.
La restauración sólo se ejecuta al crear un volumen MySQL vacío:

```powershell
mysqldump -h 127.0.0.1 -u root -p --single-transaction --routines --triggers --events --databases aaemu_login aaemu_game > aaemu-current.sql
```

```bash
docker compose --env-file .env.docker -f compose.production.yaml -f compose.restore.yaml up -d database
docker compose --env-file .env.docker -f compose.production.yaml -f compose.restore.yaml up -d
```

No vuelvas a usar `compose.restore.yaml` después del primer arranque. Los
reinicios normales usan únicamente `compose.production.yaml`.

## Copias de seguridad

El volumen `aaemu-mysql-data` contiene todo el estado persistente. Antes de una
actualización, conserva además un `mysqldump` de ambas bases. Los volúmenes
`aaemu-login-logs` y `aaemu-game-logs` guardan los logs de archivo; los logs en
vivo también están disponibles con `docker compose logs`.
