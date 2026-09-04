using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Stream;

namespace AAEmu.Game.Core.Packets.S2C;

public class TCUccCharNamePacket(ulong id, string name) : StreamPacket(TCOffsets.TCUccCharNamePacket)
{
    public override PacketStream Write(PacketStream stream)
    {
        // r575 expects uint64 before the name; uint32 shifts the string length
        // and makes StreamClientImpl reject the packet with a size mismatch.
        stream.Write(id);
        stream.Write(name);

        return stream;
    }
}
