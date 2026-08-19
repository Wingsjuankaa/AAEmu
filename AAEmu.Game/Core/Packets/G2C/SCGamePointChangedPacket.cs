using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCGamePointChangedPacket(byte kind, int amount) : GamePacket(SCOffsets.SCGamePointChangedPacket, 1)
{
    // TODO kind:
    // 0 - honor
    // 1 - vocation(living)

    public override PacketStream Write(PacketStream stream)
    {
        // AA10 r575 deserializes this packet as a byte-sized collection of
        // (kind:i32, amount:i32) entries.  The wire still uses a byte for kind,
        // but the leading collection count is mandatory; without it the client
        // consumes kind as the count and leaves the displayed balance stale.
        stream.Write((byte)1);
        stream.Write(kind);
        stream.Write(amount);
        return stream;
    }
}
