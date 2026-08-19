using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSBlessUthstinInitStatsPacketTests
{
    [Test]
    public async Task Read_ConsumesPageChangeStatAndFiveStats()
    {
        var stream = new PacketStream();
        stream.Write(2);
        stream.Write(3u);
        foreach (var stat in new uint[] { 10, 20, 30, 40, 50 })
            stream.Write(stat);

        var packet = new CSBlessUthstinInitStatsPacket();
        packet.Read(new PacketStream(stream.GetBytes()));

        await Assert.That(CSOffsets.CSBlessUthstinInitStatsPacket).IsEqualTo((ushort)0x1BD);
        await Assert.That(packet.UthstinPageIndex).IsEqualTo(2);
        await Assert.That(packet.ChangeStat).IsEqualTo(3u);
        await Assert.That(packet.Stats).IsEquivalentTo(new uint[] { 10, 20, 30, 40, 50 });
    }
}
