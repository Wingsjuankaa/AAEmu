using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCGamePointChangedPacketTests
{
    [Test]
    public async Task Body_WritesOneEntryCollectionForR575()
    {
        var stream = new PacketStream();
        new SCGamePointChangedPacket(1, -80).Write(stream);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(6);
        await Assert.That(body[0]).IsEqualTo((byte)1);
        await Assert.That(body[1]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToInt32(body, 2)).IsEqualTo(-80);
    }
}
