# Propulsión de barcos — 16 de septiembre de 2026

## Resultado y alcance

La navegación lenta de Moby Drake tiene una causa confirmada: el barco de Dannia no lleva propulsor en el hueco 27. Además se corrigen dos discrepancias de Game respecto a la Zone nativa: la suma de un motor ficticio al calcular la velocidad y la omisión del efecto de los motores básicos al instalarlos.

La corrección conserva el equipo real, el catálogo y la física nativa. No cambia velocidades de modelos ni añade motores automáticamente a barcos ya personalizados. La aceptación navegando con motor instalado queda pendiente.

## Evidencia observada

- Personaje Dannia, id 1007; Moby Drake, slave persistente 1003, plantilla 578, pergamino 16777643/38611.
- Equipamiento persistente 65585: ocho objetos en huecos 2, 3, 13, 14, 20, 21, 22 y 24. Hueco 27 vacío.
- Captura de World/Zone por TCP 1240, sin reiniciar para capturar: casco bc 1389, Zone 179. WZ movimiento tipo 5 transmite acelerador 127. ZW movimiento tipo 4 confirma acelerador 127, timón recto y velocidad horizontal aproximadamente 1,18 m/s. Las muestras rectas relevantes no indican atasco.
- Modelo 1834 → ship_models 36: velocidad 13 m/s. Coincide en full, compact original y compact de Zone.
- La plantilla del casco aporta 100 a MoveSpeedMul. La Zone usa 100/1000 × 13 = 1,3 m/s como umbral de empuje sin motor. No es un límite rígido: la velocidad resulta del equilibrio entre empuje y resistencia.

El anterior mensaje de diagnóstico de Game mostraba 14,3 porque añadía indebidamente una base de 1000. No representaba lo que la Zone estaba simulando.

## Contrato nativo

Binario x64 `x2game-dev_dedicate.dll`, SHA-256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`, base de análisis 0x39000000:

- RVA 0x237520: `ServerShipSimulationController::UpdatePhysics`. Consume aceleración 230, aceleración inversa 231 y frenado 232; son atributos distintos de la velocidad.
- RVA 0x227140: calcula el umbral a partir de velocidad del modelo y atributo 10 / 1000.
- RVA 0x258CC0 → 0xBF6C20: consulta y composición de atributos.
- RVA 0xD46070 / 0xD46470 / 0xD45BE0 → 0xBF7150: el atributo 10 cae en la base cero; no hay +1000 implícito para el casco.
- RVA 0xBF3380: composición de base, valores planos y porcentajes. Los valores planos del motor se conservan.

Los archivos de decompilación, captura y SQL están en `E:/AAEmu/rama_10/artifacts/ship-speed-20260916`. No se parchea el binario ni se cambia ZoneHost.

## Por qué falta el motor

El catálogo AA10 distingue el pergamino suelto del paquete completo:

`Moby Drake envuelto` 39362 → habilidad 31895 → efecto 52164 / GainLootPackItemEffect 2523 → paquete 11563.

Ese paquete entrega un pergamino 38611 y un `Propulsor de pesquero de Andelph` 38803 de grado 7. El equipo inicial del pergamino suelto (pack 8) omite deliberadamente el hueco del propulsor. El pack 6 del pesquero normal sí incluye 38612 en el hueco 27.

La publicación histórica de [ArcheRage NA, Marketplace Updates](https://na.archerage.to/forums/threads/marketplace-updates.658/page-6) también describe pergamino y propulsor como objetos separados del paquete. Se usa como corroboración histórica regional (`persistent_candidate`), no como autoridad de balance o protocolo. La relación exacta e IDs anteriores proceden del catálogo AA10.

No se puede concluir que todos los barcos estén limitados a 1 m/s. Un barco con motor/velas aplicados al crearse puede navegar normalmente; el filtro incorrecto afectaba especialmente al cambio de motor básico con el barco ya invocado.

## Cambios

- Los cascos simulados por Zone calculan MoveSpeedMul desde cero; los vehículos terrestres mantienen su comportamiento anterior.
- Se elimina la heurística que restaba 1000 a los motores detectados por velocidad/vida. Los buffs usan sus modificadores completos y conservan el escalado por nivel y acumulaciones.
- Un motor básico válido se envía a la Zone igual que el de grado superior. Se mantienen las validaciones de referencias y los marcadores necesarios para retirarlo de forma segura.
- El diagnóstico del umbral no inventa velocidad de modelo cuando el multiplicador es cero.

## Validación y entrega

Build Release y 4.603 pruebas correctas, sin errores ni omisiones. Siete casos nuevos cubren casco sin motor, motor básico y dos grados superiores, repetición sin duplicación, retirada del modificador, velas acumuladas, entrega real al callback de Zone y conservación de la base de unidades/vehículos terrestres.

La imagen incluye las correcciones de impuestos/grupo ya desplegadas desde la tarea paralela; sus archivos pendientes se conservan y no se incluyen en el commit de propulsión. Respaldo SQL previo y posterior a la parada limpia en el directorio de evidencia; rollback `aaemu-world:rollback-ship-speed-20260916`.

Desplegado Game/World: imagen `sha256:ab97dc8d76241af5d0982f10c1689b1ed7d586098483dd7958c9ec60f6fbdc5f`. Arranque completado a las 14:31:39 UTC, redes Game/Stream y MainWorld listas; verificación a las 14:35:38 UTC con cero reinicios. Hashes de DLL, configuración montada y evidencia en `AA10ShipPropulsion20260916.manifest.json`.

Pendiente: entregar el propulsor que acompaña al paquete original cuando Dannia esté conectada, instalarlo por la personalización nativa, comprobar navegación y conservarlo tras retirar/invocar. No se ha escrito equipo directamente en MySQL ni se ha operado el ciclo de vida de Zones.
