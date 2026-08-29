using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Housing;

/// <summary>
/// Replaces the client-side housing agent after an in-place template transition,
/// such as remodeling. A state-only refresh leaves the old template's interaction
/// provider cached in the r575 client, so the visible unit must be invalidated and
/// recreated in normal parent-before-children creation order.
/// </summary>
public static class HousingClientStateRefresh
{
    public static IReadOnlyList<GamePacket> BuildPackets(House house)
    {
        ArgumentNullException.ThrowIfNull(house);

        var packets = new List<GamePacket>
        {
            // Structural bindings are removed before this refresh. Removing the parent
            // releases the native HousingManager entry associated with the old template.
            new SCUnitsRemovedPacket([house.ObjId]),
            new SCUnitStatePacket(house),
            new SCHouseStatePacket(house)
        };

        // UnitState carries a faction only for idType 0. Recreate houses with the same
        // Invalid -> real transition used by House.AddVisibleObject.
        if (house.Faction != null)
            packets.Add(new SCUnitFactionChangedPacket(
                house.ObjId, house.Name ?? "", FactionsEnum.Invalid, house.Faction.Id, false));

        var doodads = house.AttachedDoodads.ToArray();
        for (var i = 0; i < doodads.Length; i += SCDoodadsCreatedPacket.MaxCountPerPacket)
        {
            var length = Math.Min(SCDoodadsCreatedPacket.MaxCountPerPacket, doodads.Length - i);
            var chunk = new Doodad[length];
            Array.Copy(doodads, i, chunk, 0, length);
            packets.Add(new SCDoodadsCreatedPacket(chunk));
        }

        packets.Add(new SCHouseDataPacket([house]));
        packets.Add(new SCHouseBuildProgressPacket(
            house.TlId,
            house.ModelId,
            house.AllAction,
            house.CurrentStep == -1 ? house.AllAction : house.CurrentAction));
        return packets;
    }

    public static void Broadcast(House house)
    {
        foreach (var packet in BuildPackets(house))
            house.BroadcastPacket(packet, true);
    }
}
