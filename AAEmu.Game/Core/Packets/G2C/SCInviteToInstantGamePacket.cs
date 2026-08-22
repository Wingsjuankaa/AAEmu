using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCInviteToInstantGamePacket(
    int invitationTime,
    ZoneInstanceId zoneInstanceId,
    uint type,
    ulong matchingKey,
    uint accept,
    uint maxEntry)
    : GamePacket(SCOffsets.SCInviteToInstantGamePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(invitationTime);
        stream.Write(zoneInstanceId);
        stream.Write(type);
        stream.Write(matchingKey);

        // r575 serializes an embedded packet buffer before matchingInviteInfo.
        // Its empty representation is an outer two-byte size plus an inner zero size.
        stream.Write((ushort)2);
        stream.Write((ushort)0);

        stream.Write(accept);
        stream.Write(maxEntry);
        return stream;
    }
}
