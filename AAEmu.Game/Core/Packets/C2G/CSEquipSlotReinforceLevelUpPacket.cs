using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.GameData;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Native r575 level-up confirmation. EXP feeding remains a separate cast.
/// </summary>
/// <remarks>
/// The body is the slot alone — the item the step costs comes from the ladder, not from the client.
/// </remarks>
public class CSEquipSlotReinforceLevelUpPacket() : GamePacket(CSOffsets.CSEquipSlotReinforceLevelUpPacket, 1)
{
    public sbyte EquipSlot { get; private set; }

    public override void Read(PacketStream stream)
    {
        EquipSlot = stream.ReadSByte();
        if (EquipSlot >= 0)
            Connection.ActiveChar?.EquipSlotReinforce?.LevelUp((byte)EquipSlot);
    }
}
