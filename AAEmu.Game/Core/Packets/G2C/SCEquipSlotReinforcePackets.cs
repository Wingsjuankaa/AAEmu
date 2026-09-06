using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

// r575 constructors/serializers: 3D6DB0/AA54E0, 3D6E90/AA55E0, 3D6F70/AA56E0.
public sealed class SCEquipSlotReinforceUpdatePacket(uint objectId, byte slot, sbyte level, int experience)
    : GamePacket(SCOffsets.SCEquipSlotReinforceUpdatePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.WriteBc(objectId);
        stream.Write(slot);
        stream.Write(level);
        stream.Write(experience);
        return stream;
    }
}

public sealed class SCEquipSlotReinforceLevelEffectUpdatePacket(uint objectId, byte slot, sbyte level, uint modifierId)
    : GamePacket(SCOffsets.SCEquipSlotReinforceLevelEffectUpdatePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.WriteBc(objectId);
        stream.Write(slot);
        stream.Write(level);
        stream.Write(modifierId);
        return stream;
    }
}

public sealed class SCEquipSlotReinforceLevelEffectDeletePacket(uint objectId, byte slot, sbyte level)
    : GamePacket(SCOffsets.SCEquipSlotReinforceLevelEffectDeletePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.WriteBc(objectId);
        stream.Write(slot);
        stream.Write(level);
        return stream;
    }
}
