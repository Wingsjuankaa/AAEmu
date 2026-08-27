using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCCraftFailedPacketTests
{
    [Test]
    public async Task WritesR575TypeCountAndProductTypesInOrder()
    {
        var stream = new PacketStream();
        new SCCraftFailedPacket(5544, [101, 202]).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(SCOffsets.SCCraftFailedPacket).IsEqualTo((ushort)0x22D);
        await Assert.That(body.ReadInt32()).IsEqualTo(5544);
        await Assert.That(body.ReadUInt32()).IsEqualTo(2u);
        await Assert.That(body.ReadInt32()).IsEqualTo(101);
        await Assert.That(body.ReadInt32()).IsEqualTo(202);
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }

    [Test]
    public async Task CapsFailedProductListAtNativeTwentyEntries()
    {
        var stream = new PacketStream();
        new SCCraftFailedPacket(1, Enumerable.Range(1, 25).ToArray()).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        body.ReadInt32();
        await Assert.That(body.ReadUInt32()).IsEqualTo(20u);
        await Assert.That(Enumerable.Range(0, 20).Select(_ => body.ReadInt32()).ToArray())
            .IsEquivalentTo(Enumerable.Range(1, 20).ToArray());
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }
}
