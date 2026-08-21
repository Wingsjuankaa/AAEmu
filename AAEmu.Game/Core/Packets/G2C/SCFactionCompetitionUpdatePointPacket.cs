using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 live scoreboard update: zone-group i16, faction i32, points u32.</summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class SCFactionCompetitionUpdatePointPacket(short @type, int @type2, uint nUpdatePoint) : GamePacket(SCOffsets.SCFactionCompetitionUpdatePointPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(@type);
        stream.Write(@type2);
        stream.Write(nUpdatePoint);
        return stream;
    }
}
