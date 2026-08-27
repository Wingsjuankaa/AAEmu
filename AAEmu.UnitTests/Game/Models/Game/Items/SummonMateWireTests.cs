using System.Buffers.Binary;
using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class SummonMateWireTests
{
    [Test]
    public async Task SnapshotWritesExactR575TwentyByteMateBody()
    {
        var item = new SummonMate
        {
            DetailMateExp = 0x01020304,
            DetailLevel = 27
        };
        var stream = new PacketStream();

        item.WriteDetails(stream);
        var body = stream.GetBytes();

        await Assert.That(body).Count().IsEqualTo(20);
        await Assert.That(BinaryPrimitives.ReadInt32LittleEndian(body.AsSpan(0, 4)))
            .IsEqualTo(0x01020304);
        await Assert.That(body[4]).IsEqualTo((byte)0);
        await Assert.That(body[5]).IsEqualTo((byte)27);
        await Assert.That(body.AsSpan(6).ToArray()).IsEquivalentTo(new byte[14]);
    }

    [Test]
    public async Task SnapshotRoundTripPreservesKnownFields()
    {
        var source = new SummonMate { DetailMateExp = 123456, DetailLevel = 44 };
        var writer = new PacketStream();
        source.WriteDetails(writer);
        var target = new SummonMate();

        target.ReadDetails(new PacketStream(writer.GetBytes()));

        await Assert.That(target.DetailMateExp).IsEqualTo(123456);
        await Assert.That(target.DetailLevel).IsEqualTo((byte)44);
    }
}
