namespace AAEmu.Game.Models.Game.GmPanel;

public sealed record GmPanelDescription(string Category, string Description, string Example, bool Confirm);

public static class GmPanelDescriptions
{
    // Keyed by implementation, not aliases: duplicate registrations resolve as the dispatcher does.
    // es_ES editorial unit: implementation type + description. Native tokens remain unchanged.
    private const string Rows = """
ActabilityCmd|progress|Ajustar puntos y etapa de una competencia.| |0
AddBadges|progress|Añadir puntos de vocación al personaje.|1000|0
AddBuff|combat|Ver, aplicar o retirar buffs del objetivo. ID negativo: retirar.|View|0
AddCargoMaterials|economy|Añadir existencias de prueba a las colas de materiales de cargamento.||1
AddGold|economy|Añadir o retirar dinero del objetivo.|1|0
AddLabor|progress|Añadir Labor al objetivo.|1000|0
AddPortals|move|Registrar un destino en el libro de teletransporte.||0
AddXP|progress|Añadir experiencia al objetivo.|1000|0
AlphaAccess|admin|Conceder o retirar acceso individual a la alpha privada.||1
Announce|admin|Emitir un anuncio para todo el servidor.||1
Appellation|progress|Añadir un título por ID.||0
ArchePassCmd|progress|Consultar y probar la progresión del ArchePass.||0
Around|inspect|Listar objetos próximos por tipo y radio.|all 30|0
BuildHouse|housing|Avanzar etapas de construcción de la casa seleccionada.|1|0
ChangeLevel|progress|Añadir la experiencia necesaria para alcanzar un nivel.||0
ClaimTerritory|guild|Reclamar un territorio para una facción o gremio.||1
ClearCombat|combat|Limpiar el indicador de combate del cliente; no borra el estado del servidor.||0
CofferActions|housing|Consultar o modificar un cofre del mundo.||1
Damage|combat|Aplicar daño a ti o al objetivo, fijo o porcentual.|1|0
DeliverTradePackMails|economy|Liberar correos pendientes de recompensas de mercancías.||1
Despawn|world|Retirar un NPC o doodad por objeto, o por plantilla y radio.||1
DeSpawnAll|world|Retirar todos los objetos del mundo.||1
DisableCastleZone|guild|Bloquear nuevas reclamaciones de castillo en un grupo de zonas.||1
DisconnectMe|admin|Desconectar tu personaje.||1
Dist|inspect|Consultar la distancia al objetivo o a un objeto.||0
DominionPoint|guild|Consultar uso de puntos de dominio o concederlos para una zona.||0
DominionZoneResync|guild|Reenviar a Zone los datos del territorio reclamado.||1
DoodadCmd|world|Administrar objetos interactivos mediante sus subcomandos.||0
DoodadLocationCmd|world|Cambiar la posición de un doodad; * conserva una coordenada.||0
DumpSpecialtyEvents|economy|Consultar los eventos de especialidades comerciales.||0
EnableCastleZone|guild|Retirar el bloqueo de reclamaciones de castillo.||1
EndGuildProtection|guild|Terminar la protección de guerra del gremio indicado.||1
Ezi|world|Crear una zona temporal de Ezi para reparar y personalizar barcos.|300|0
FailSkill|debug|Provocar un fallo de habilidad con un resultado específico.||0
FeatureCmd|admin|Consultar o modificar opciones de funciones del servidor.||1
FindObject|inspect|Buscar objetos cercanos de una plantilla concreta.||0
FishFinderCmd|world|Administrar el buscador de bancos de peces.||0
FishSchoolCountCmd|inspect|Contar bancos de peces presentes en el mundo.||0
FishSpots|world|Consultar y administrar puntos de pesca de prueba.||0
Fly|move|Activar o desactivar el vuelo del objetivo.|true|0
GardenRate|world|Consultar o ajustar la tasa del Jardín.||1
GearScore|inspect|Consultar la puntuación de equipo calculada por el servidor.||0
GetAttribute|inspect|Consultar atributos del objetivo.|all|0
GetPosition|inspect|Consultar la posición del personaje.||0
GimmickCmd|world|Administrar gimmicks mediante sus subcomandos.||0
GiveBlackPearlKit|items|Entregar el kit de prueba de Black Pearl.||0
GmIcon|admin|Mostrar u ocultar el icono GM junto a tu nombre.||0
GodMode|combat|Activar o desactivar la inmortalidad frente a otros jugadores.|true|0
GoldCmd|economy|Administrar dinero mediante sus subcomandos.||0
GuildExp|guild|Añadir experiencia a tu gremio y actualizar su nivel.|1000|0
GuildPrestige|guild|Añadir contribución o prestigio a un miembro del gremio.|100|0
GuildResidence|housing|Demoler forzosamente la residencia de tu gremio.|demolish|1
GuildWarEnd|guild|Terminar la guerra de tu gremio; wipe elimina recompensas y protección.||1
GuildWarTime|guild|Ajustar la duración de futuras guerras de gremios.||1
Heal|combat|Restaurar salud y maná del objetivo seleccionado o del personaje indicado.||0
Height|inspect|Comparar altura del personaje y del terreno.||0
Help|inspect|Listar los comandos disponibles y su ayuda.||0
HeroPhaseCmd|guild|Consultar o forzar la fase del ciclo de héroes.||1
HouseBindingMove|housing|Mover un punto de anclaje de una casa.||0
HouseRebuild|housing|Consultar paquetes de reconstrucción y destinos posibles.||0
IgnoreCooldowns|combat|Activar o desactivar el modo sin cooldown. Conserva el GCD y las cadenas.|true|0
InGameCashShop|economy|Activar, desactivar o recargar la tienda del juego.||1
Invisible|combat|Hacerte invisible o visible para otros jugadores.|true|0
ItemCmd|items|Añadir, caducar o desenvolver objetos. El subcomando define la acción.||0
Kick|admin|Expulsar a un personaje e indicar un motivo.||1
Kill|combat|Matar al objetivo seleccionado.||1
AddKit|items|Entregar un conjunto de objetos por nombre de kit.||0
Leadership|guild|Consultar o modificar cifras de liderazgo.||0
Move|move|Moverte o mover un personaje a coordenadas o a tu posición.||0
MoveAll|move|Traer a todos los jugadores a tu posición.||1
MoveTo|move|Grabar, guardar y reproducir rutas de movimiento.||0
NpcCmd|world|Administrar NPC mediante sus subcomandos.||0
Nudge|move|Avanzar una distancia desde tu posición.|5|0
Nwrite|world|Guardar posición y rotación del doodad en el archivo de spawns.||1
ObjectPosition|world|Cambiar coordenadas locales de un objeto.||0
ObjectRotation|world|Cambiar la rotación local de un objeto en grados.||0
Online|inspect|Listar personajes conectados, con filtro opcional.||0
PingPosition|inspect|Mostrar la posición señalada en el mapa.||0
QaInspect|inspect|Inspeccionar salud, buffs, plot o equipo sin modificar el estado.|self|0
QuestCmd|progress|Consultar o modificar misiones y objetivos.||0
RankRefresh|guild|Recalcular todas las clasificaciones.||1
ReloadAuction|economy|Recargar el administrador de subastas.||1
ReloadConfigs|admin|Recargar la configuración del servidor.||1
ResetSkillCooldowns|combat|Limpiar cooldowns de habilidades y grupos compartidos. Conserva el GCD.||0
Revive|combat|Resucitar al objetivo.||0
Rotate|world|Girar el objetivo hacia ti o al ángulo indicado.||0
Run|move|Alternar el buff de carrera 3105 del personaje objetivo.||0
Scripts|admin|Recargar scripts, guardar, reiniciar o apagar Game.||1
SendPacket|debug|Enviar un paquete de prueba desde hexadecimal o un archivo.||1
SensitiveOperation|debug|Probar operaciones sensibles; consultar la ayuda del servidor.||1
SetFaction|world|Consultar o cambiar la facción del objetivo.||0
SetSpecialtyEvent|economy|Cambiar un evento de especialidades comerciales.||1
SetTradePackMailDelay|economy|Cambiar la espera del correo de recompensas de mercancías.||1
ShowInventory|inspect|Inspeccionar un inventario; fix solicita reparación.||0
SiegeWindow|guild|Consultar equipos o forzar la ventana de declaración de asedio.||1
SlaveCmd|world|Administrar vehículos y monturas mediante sus subcomandos.||0
Snow|world|Activar o desactivar la nieve en todo el servidor.|true|1
SoloParty|combat|Crear un grupo formado solo por tu personaje.||0
Spawn|world|Crear un NPC o doodad. npc dummy crea el muñeco de pruebas.|npc dummy|0
SpawnGrid|world|Crear una cuadrícula de NPC o doodads.||1
SpawnTradePack|economy|Crear y equipar una mercancía nueva de su zona de producción.||0
Speed|move|Ajustar velocidad nativa: cada nivel añade 1 %. reset restaura.|reset|0
Sphere|world|Listar o administrar esferas y sus misiones.||0
Stats|combat|Consultar o ajustar modificadores GM de estadísticas.|show|0
Teleport|move|Teletransportarte a un destino por nombre.||0
TestChatChannel|debug|Enviar paquetes de unión o salida de canales para pruebas.||0
TestCombat|debug|Probar notificaciones del estado de combate.||0
TestEcho|debug|Repetir texto en el chat.|Prueba GM|0
TestFSets|inspect|Mostrar los fsets activos del servidor.||0
TestHeight|debug|Visualizar pruebas de altura del terreno.||0
TestHouse|housing|Probar acciones de vivienda, incluida su venta.||1
TestMails|debug|Probar acciones de correo o enviarte un correo de prueba.||0
TestSlave|world|Crear un vehículo o montura de prueba.||0
TestTracker|debug|Alternar información de depuración de movimiento del objetivo.||0
TestTransfer|world|Crear un vehículo de transporte.||0
TestZoneState|world|Cambiar el estado de una zona.||1
TickDoodad|world|Avanzar el doodad indicado a la siguiente fase.||0
TimeCmd|world|Consultar o ajustar la hora del mundo.||1
TowerDef|world|Listar y controlar eventos de oleadas del mundo.||1
Trial|debug|Probar las etapas de un juicio.||1
UnclaimTerritory|guild|Liberar un territorio reclamado.||1
UseSkill|combat|Forzar una habilidad por ID sobre una unidad o área.||0
WaterDebugCmd|debug|Consultar o recargar datos de agua y controlar la sonda.||0
WorldCmd|admin|Consultar o ajustar parámetros globales del mundo.||1
ZoneTeleport|move|Teletransportarte al centro aproximado de una zoneKey.||0
""";
    private static readonly Dictionary<string, GmPanelDescription> Data = Rows.Split('\n', StringSplitOptions.RemoveEmptyEntries)
        .Select(line => line.Trim().Split('|')).ToDictionary(p => p[0], p => new GmPanelDescription(p[1], p[2], p[3].Trim(), p[4] == "1"));
    public static GmPanelDescription Get(string implementation) => Data.GetValueOrDefault(implementation,
        new("debug", "Comando del servidor. Consulta su sintaxis y ayuda antes de ejecutarlo.", "", true));
    internal static bool Has(string implementation) => Data.ContainsKey(implementation);
}
