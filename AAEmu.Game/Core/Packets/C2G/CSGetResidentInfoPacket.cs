using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Requests the active character's AA10 resident state for a zone group.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class CSGetResidentInfoPacket() : GamePacket(CSOffsets.CSGetResidentInfoPacket, 1)
{
    public short TypeValue { get; private set; }
    public ulong TypeValue2 { get; private set; }

    public override void Read(PacketStream stream)
    {
        TypeValue = stream.ReadInt16();
        TypeValue2 = stream.ReadUInt64();
    }

    public override void Execute()
    {
        var character = Connection.ActiveChar;
        if (TypeValue > 0 && (TypeValue2 == 0 || TypeValue2 == character.Id))
            QuestRewardProgressManager.Instance.SendResidentInfo(character, (uint)TypeValue);
    }
}
