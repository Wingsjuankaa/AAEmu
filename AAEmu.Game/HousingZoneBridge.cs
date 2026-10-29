using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Housing;

using NLog;

namespace AAEmu.Game;

/// <summary>
/// </summary>
public static class HousingZoneBridge
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

    public static void NotifyZoneHouseCreated(House house)
    {
        if (!WorldIntegration.ZoneAuthority || house == null)
            return;

        try
        {
            var zoneId = house.Transform?.ZoneId ?? 0;
            var unitStateBody = WorldIntegration.BuildWzUnitStateBody(house);
            var houseStateBody = BuildHouseStateBody(house);
            WorldIntegration.RelayHouseStateToZone?.Invoke(zoneId, unitStateBody, houseStateBody);
            NotifyZoneHouseBuildState(house);

            Logger.Debug(
                "WZUnitState/WZHouseState and AA10 bindings queued for house db={0} obj={1} zoneId={2}",
                house.Id, house.ObjId, zoneId);
        }
        catch (Exception ex)
        {
            Logger.Warn(ex, "Failed to relay house {0} to Zone", house.Id);
        }
    }

    public static void NotifyZoneHouseBuildState(House house)
    {
        if (!WorldIntegration.ZoneAuthority || house == null)
            return;

        var zoneId = house.Transform?.ZoneId ?? 0;
        if (house.CurrentStep >= 0)
        {
            WorldIntegration.RelayHouseBuildProgressToZone?.Invoke(
                zoneId, house.TlId, house.ModelId, house.AllAction, house.CurrentAction);
        }
        else
        {
            WorldIntegration.RelayHouseBuildDoneToZone?.Invoke(zoneId, house.TlId);
            HousingBindingRuntime.RelayToZone(house);
        }
    }

    /// <summary>
    /// Removes a World-deleted house from the Zone simulation after its attached doodads have
    /// been torn down. WZUnitRemoved is keyed by the house's unit object ID, while routing must
    /// </summary>
    public static void NotifyZoneHouseRemoved(uint zoneId, uint houseObjId)
    {
        if (!WorldIntegration.ZoneAuthority || zoneId == 0 || houseObjId == 0)
            return;

        WorldIntegration.RelayUnitRemovedToZoneId?.Invoke(zoneId, houseObjId);
        Logger.Debug("WZUnitRemoved queued for house obj={0} zoneId={1}", houseObjId, zoneId);
    }

    /// <summary>
    /// </summary>
    public static byte[] BuildHouseStateBody(House house)
    {
        // Game and Zone consume the same native house-state layout, including category and UCC slots.
        return house.Write(new PacketStream()).GetBytes();
    }

    private static void WriteWorldPosition(PacketStream stream, float x, float y, float z)
    {
        stream.Write(Helpers.ConvertLongX(x));
        stream.Write(Helpers.ConvertLongY(y));
        stream.Write(z);
    }
}
