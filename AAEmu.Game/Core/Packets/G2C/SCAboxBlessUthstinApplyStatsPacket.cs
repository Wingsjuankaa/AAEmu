using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// TODO: nothing constructs this packet yet.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class SCAboxBlessUthstinApplyStatsPacket(uint bc, bool bResult, IReadOnlyList<int> stats, int pageIndex) : GamePacket(SCOffsets.SCAboxBlessUthstinApplyStatsPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        if (stats?.Count != 5)
            throw new ArgumentException("Bless Uthstin packets require exactly five stats.", nameof(stats));
        stream.WriteBc(bc);
        stream.Write(bResult);
        foreach (var stat in stats)
            stream.Write(stat);
        stream.Write(pageIndex);
        return stream;
    }
}
