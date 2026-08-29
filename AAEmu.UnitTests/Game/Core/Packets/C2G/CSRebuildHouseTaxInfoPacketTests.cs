using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSRebuildHouseTaxInfoPacketTests
{
    [Test]
    public async Task NativeR575BodyReadsTimelineIdAsUnsignedSixteenBits()
    {
        var stream = new PacketStream([0x34, 0x12]);

        var timelineId = CSRebuildHouseTaxInfoPacket.ReadHouseTimelineId(stream);

        await Assert.That(timelineId).IsEqualTo((ushort)0x1234);
        await Assert.That(stream.HasBytes).IsFalse();
    }
}
