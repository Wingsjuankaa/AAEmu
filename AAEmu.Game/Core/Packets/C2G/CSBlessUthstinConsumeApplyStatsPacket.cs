using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>Consumes the exact selected Migration Scaling item and requests a server-side roll.</summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class CSBlessUthstinConsumeApplyStatsPacket() : GamePacket(CSOffsets.CSBlessUthstinConsumeApplyStatsPacket, 1)
{
    public long Item { get; private set; }
    public int PageIndex { get; private set; }

    public override void Read(PacketStream stream)
    {
        Item = stream.ReadInt64();
        PageIndex = stream.ReadInt32();

        var itemInstanceId = Item > 0 ? checked((ulong)Item) : 0;
        Connection?.ActiveChar?.BlessUthstin?.TryConsumeApplyStats(itemInstanceId, PageIndex);
    }
}
