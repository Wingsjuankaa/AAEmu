using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>Exact r575 incremental ArchePass-state update serializer.</summary>
public class SCUpdateArchePassPacket(
    ArchePassWireState state,
    byte reason,
    int diffPoint,
    bool allDone) : GamePacket(SCOffsets.SCUpdateArchePassPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        state.Write(stream);
        stream.Write(reason);
        stream.Write(diffPoint);
        stream.Write(allDone);
        return stream;
    }
}
