# World Level r575: desactivación por decisión del usuario

Fecha: 2026-09-04. Target: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`.
Baseline revisado: HEAD `bdad11fec1493c43a854369e707de72a20f26f86`, padre exacto
`upstream/client_version/zone-10.0.2_r575` (`3cc280b14d7da0d874121d14ebbf409f5e032d1c`).

## Decisión y alcance

El usuario autorizó quitar esta mecánica si faltaba demasiada información. El
cliente y la Zone disponibles permiten reconstruir tablas y presentación, pero
no el productor original del nivel mundial, su población/cadencia ni la aplicación
autoritativa de EXP por fuente y su orden de redondeo. No se inventó una fórmula.
La reconstrucción completa queda retirada de la cola activa por esta decisión.

El cambio final pone `system_feature_controls.state=0` exclusivamente en la entidad
`id=1, control_type=1, condition_type=1001`, descripción
`World Level System - Opens at player level 30`. Se conservan sus demás columnas
y el control de Sailing Activity. Se aplica por separado a las compact embedded
y loose actuales; tienen identidades diferentes y no se intercambian.

No se modifica experiencia, personajes, fecha de apertura, tablas `world_level_*`,
SQLite forense original, código de premios o restricciones del servidor. El
servidor existente no implementaba multiplicadores World Level autoritativos.
El paquete legado conserva su cuerpo y orden de inicialización: el interruptor
del cliente desactiva sus consumidores visibles, no fabrica un nuevo nivel.
No se requiere reiniciar Game o Zones por este parche de datos del cliente.

Los borradores de catálogo, pruebas y traducción preparados antes de esta decisión
se retiraron del árbol activo y se conservaron en el output forense `retired-drafts`.
Las traducciones propuestas nunca se instalaron en el cliente.

## Contrato nativo confirmado

Binario x64 efectivo `Bin64/x2game.dll`, SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
Todas las funciones usadas se compararon byte a byte con este binario, además
de decompilar el proyecto Ghidra; no se trasladaron direcciones desde AA8.

| RVA | Contrato |
|---|---|
| `0xB82E30` | Loader de `system_feature_controls`; `state` admite 0/1. |
| `0xB74930` | Selección de controles por `control_type`, aquí 1. |
| `0x354D60` | `IsWorldLevelEnabled`: devuelve falso si el control no tiene `state=1`, antes de evaluar la condición de nivel. |
| `0xB74120` | Resolución de la condición, irrelevante cuando el control está apagado. |
| `0xA95630` | Serialización de los seis campos World Level. |
| `0x346880` | Handler que copia el nivel a ClientPlayer y emite `WORLDLEVEL_CHANGED`. |

**Corrección al diagnóstico preliminar:** la habilitación sale de
`system_feature_controls`, no del quinto campo de `SCWorldLevelInfo` ni de
`SCWorldContent`. El loader nativo cierra esta identificación sin depender del
nombre usado en comentarios antiguos.

Los ALB x64 efectivos confirman consumidores del mismo interruptor:
unitframe/player (emblema), characterinfo/character_info_view (emblema y guía),
questcontext/common (flechas de EXP) y quest_context_directing (flechas y bloqueo
de aceptación). Cuando está apagado, los predicados de límite y hard cap de
misiones retornan falso antes de consultar las tablas.

El paquete capturado `(42,6,10000,0,1,-41)` significa nivel mundial, días del
servidor, modificador EXP, hard cap, nivel del personaje y diferencia firmada.
`-41=1-42`; el quinto campo no es una habilitación. Sus comentarios se corrigieron
sin alterar bytes. El cliente calcula los porcentajes mostrados desde las tablas:
200%, 150%, 120%, 100%, 90%, 80%, 65%, 50% por diferencia inclusiva; son datos
de presentación demostrados, no prueba de ganancias autoritativas restauradas.
El hard cap tiene tramos de días 0–1, 2…8 y 9–9999. La fecha se compara por
calendario local; no se implementó una aproximación por periodos de 24 horas.

## Parche reproducible

Builder: `Scripts/PatchAa10WorldLevelDisabled.py`.
Aplicador: `Scripts/ApplyAa10WorldLevelDisabled.py` (dry-run por defecto).
Ambos rechazan hashes desconocidos; el builder exige la identidad semántica,
integridad SQLite, tamaño idéntico y resultado determinista. No acepta las
compact generadas por el borrador de traducción retirado.

| Artefacto | SHA-256 original | SHA-256 desactivado |
|---|---|---|
| Embedded, 440823808 bytes | `FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5` | `8F39B0672B60F77B4027259BDFFB714810BF9392045BA81686A028203ADB5223` |
| Loose, 440836096 bytes | `F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B` | `90E5C12A451F1334FF5C1B949982BEE3F1A9E4258F0EFC5FD3FF9D0478591E3C` |

Desde la raíz del repositorio:

```powershell
python -B Scripts/ApplyAa10WorldLevelDisabled.py
python -B Scripts/ApplyAa10WorldLevelDisabled.py --apply
# Primero dry-run del rollback; añadir --apply para restaurar ambas entradas.
python -B Scripts/ApplyAa10WorldLevelDisabled.py --rollback <manifest-de-instalacion.json>
```

El aplicador conserva originales y manifiesto bajo
`E:\AAEmu\rama_10\backups\client-patches\aa10-world-level-disabled-<fecha>`;
reextrae la entrada, comprueba hashes y tamaño, y registra SHA-256 completo del
paquete antes/después. No opera con `archeage.exe` abierto. Un fallo revierte
lo modificado cuando la identidad permite hacerlo sin sobrescribir deriva ajena.

## Evidencia y aceptación

Output durable:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\world-level-frontier`.
Incluye native-client/native-zone/native-disable, sus identidades byte a byte,
SQL originales, ALB efectivos decompilados, borradores retirados y logs de pruebas.

- Builder: 4 pruebas correctas (identidad, rechazo sin mutación, aislamiento,
  idempotencia y liberación del archivo SQLite antes de entregarlo a AAPak).
- `dotnet restore`, build Release y suite unitaria: 1804 correctas, 0 fallos.
- Control Center: typecheck, 52 pruebas correctas/1 omitida, smoke SQLite y build correctos.
- Control Center invalida su caché por ruta/tamaño/mtime; SHA completo es informativo.
  No existe una allowlist cerrada que deba ampliarse para este parche.
- La aceptación visual requiere abrir el cliente nuevamente: comprobar ausencia
  del emblema dorado, guía World Level y flechas World Level de EXP, y aceptar
  una misión normal. Esta comprobación no se sustituye por las pruebas estáticas.

El checkpoint adjunto registra el resultado real de aplicación y las verificaciones
pendientes. La reconstrucción original no se declara terminada: fue descartada
por falta de contrato nativo suficiente y sustituida por la desactivación autorizada.
