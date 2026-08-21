using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Notifies the family of its current level/experience and identifies the contributing character.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class SCFamilyExpChangeNotifyPacket(int familyId, ulong contributorId, uint level, uint exp) : GamePacket(SCOffsets.SCFamilyExpChangeNotifyPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(familyId);
        stream.Write(contributorId);
        stream.Write(level);
        stream.Write(exp);
        return stream;
    }
}
