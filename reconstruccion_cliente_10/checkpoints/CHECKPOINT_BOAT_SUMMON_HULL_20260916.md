# Barcos: volumen del casco y fondo de lagos

Aceptación posterior: el usuario confirmó «eso quedó arreglado» al pasar al
diagnóstico de honor por NPC. Se registra aceptación funcional de la invocación;
no se infiere que haya probado todos los barcos o completado todos los casos.

Target `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, base b22b3ccfc.
Padre exacto `upstream/client_version/zone-10.0.2_r575` b439e1cc0, integrado.
No merge, commit ni push adicionales en esta entrega.

Diagnóstico, RVAs, límites y aceptación:
[AA10BoatSummonHullClearance_es.md](../../Docs/AA10BoatSummonHullClearance_es.md).

Se corrige el rechazo de Moby Drake por exigir 14,3 m derivados de la caja de masa;
su caja nativa requiere 1,749273 m al aparecer en superficie. Cargador de OBB,
heightmap XY y comprobación del terreno bajo el volumen orientado. Fallback previo
conservado para nueve templates sin geometría. No se cambia física ni balance.

4.631 pruebas correctas. Desplegado Game/World con respaldo e identidad registrada
en el manifest. Las ediciones concurrentes posteriores en ItemManager y
LootingContainer se conservaron fuera del ensamblado de esta entrega. Pendiente
aceptación de usuario en lago, costa y pesquero normal. No operar lifecycle de Zones.
