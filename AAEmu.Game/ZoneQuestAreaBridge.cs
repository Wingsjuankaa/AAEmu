using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;

using NLog;

namespace AAEmu.Game;

/// <summary>
/// Bridges Zone <c>ZWEnterArea</c>/<c>ZWLeaveArea</c> (quest_area + district) into World quest logic.
/// </summary>
public static class ZoneQuestAreaBridge
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

    public static void OnEnter(uint unitId, uint areaId, int v1, int v2)
    {
        if (!WorldIntegration.ZoneAuthority)
            return;

        var ch = ResolveCharacter(unitId);
        if (ch == null)
        {
            Logger.Debug("ZoneEnterArea: no character for unit={0} area={1}", unitId, areaId);
            return;
        }

        Logger.Info("Quest area ENTER char={0} area={1} v1={2} v2={3}", ch.Name, areaId, v1, v2);
        if (TryGetBookDistrict(areaId, v1, out var districtId))
        {
            ch.Portals.NotifyDistrict(districtId);
            return;
        }
        try
        {
            // Hook for quest components that key off area id (district / quest_area).
            ch.Quests?.OnZoneAreaEnter(areaId);
        }
        catch (Exception ex)
        {
            Logger.Warn(ex, "OnZoneAreaEnter failed for {0} area={1}", ch.Name, areaId);
        }
    }

    // r575 ZWEnterArea serializes groupId:u8, value1:i32, value2:i32.
    // district.xml Area Group=22 stores district_id in value1, not Area.Id (usually zero).
    internal static bool TryGetBookDistrict(uint groupId, int value1, out uint districtId)
    {
        districtId = groupId == 22 && value1 > 0 && value1 < PortalVisitKey.DistrictTag
            ? (uint)value1 : 0;
        return districtId != 0;
    }

    public static void OnLeave(uint unitId, uint areaId, int v1, int v2)
    {
        if (!WorldIntegration.ZoneAuthority)
            return;

        var ch = ResolveCharacter(unitId);
        if (ch == null)
            return;

        Logger.Info("Quest area LEAVE char={0} area={1} v1={2} v2={3}", ch.Name, areaId, v1, v2);
        try
        {
            ch.Quests?.OnZoneAreaLeave(areaId);
        }
        catch (Exception ex)
        {
            Logger.Warn(ex, "OnZoneAreaLeave failed for {0} area={1}", ch.Name, areaId);
        }
    }

    private static Character ResolveCharacter(uint unitId)
    {
        var world = WorldManager.Instance.GetWorld(WorldManager.DefaultInstanceId);
        return world?.GetCharacterByObjId(unitId);
    }
}
