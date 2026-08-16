using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Replaces the 34 per-slot equipment-modifier activation booleans on an existing unit.
/// The packet name preserves the spelling exported by the r575 binary.
/// </summary>
public sealed class SCUnitEquipmentsRndAttrUnitModifierAvtivateChangedPacket(Unit unit)
    : GamePacket(SCOffsets.SCUnitEquipmentsRndAttrUnitModifierAvtivateChangedPacket, 1)
{
    private readonly ulong _flags = EquipmentSerializer.GetActivationFlags(unit);

    public override PacketStream Write(PacketStream stream)
    {
        stream.WriteBc(unit.ObjId);
        stream.Write(_flags);
        return stream;
    }

    public override string Verbose() => $" - unit={unit.ObjId}, activationFlags=0x{_flags:X16}";
}
