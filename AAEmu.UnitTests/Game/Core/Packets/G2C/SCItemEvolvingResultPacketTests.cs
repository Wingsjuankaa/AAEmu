using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemEvolvingResultPacketTests
{
    [Test]
    public async Task ResultBody_CarriesChangeAttemptsAndOnlyAddedEffects()
    {
        var item = new Item { Id = 0x0102030405060708 };
        var packet = new SCItemEvolvingResultPacket(
            item,
            6,
            3,
            983,
            17,
            3,
            [new SCItemEvolvingResultPacket.EvolvingAttribute(82, 0, 31)]);
        var stream = new PacketStream();

        packet.Write(stream);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(30);
        await Assert.That(BitConverter.ToUInt64(body, 0)).IsEqualTo(item.Id);
        await Assert.That(body[8]).IsEqualTo((byte)6);
        await Assert.That(body[9]).IsEqualTo((byte)3);
        await Assert.That(body[10]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToInt32(body, 11)).IsEqualTo(983);
        await Assert.That(BitConverter.ToInt32(body, 15)).IsEqualTo(17);
        await Assert.That(BitConverter.ToInt32(body, 19)).IsEqualTo(3);
        await Assert.That(BitConverter.ToUInt16(body, 23)).IsEqualTo((ushort)82);
        await Assert.That(body[25]).IsEqualTo((byte)0);
        await Assert.That(BitConverter.ToInt32(body, 26)).IsEqualTo(31);
    }
}
