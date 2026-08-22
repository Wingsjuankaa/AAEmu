using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.InstantGame.Static;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCAppliedToInstantGamePacket(uint instanceId, InstantCorps corps, ushort errorMessageId = 0)
    : GamePacket(SCOffsets.SCAppliedToInstantGamePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(instanceId);
        stream.Write((byte)corps);
        stream.Write(errorMessageId);
        return stream;
    }
}
