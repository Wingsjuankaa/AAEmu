using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCAccountAttendancePacket(uint count)
    : GamePacket(SCOffsets.SCAccountAttendancePacket, 5)
{
    public override PacketStream Write(PacketStream stream)
    {
        for (var i = 0; i < count; i++)
        {
            stream.Write(DateTime.MinValue);
            stream.Write(false);
        }
        return stream;
    }
}
