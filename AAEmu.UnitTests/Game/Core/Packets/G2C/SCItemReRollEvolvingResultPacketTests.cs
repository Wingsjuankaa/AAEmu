using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemReRollEvolvingResultPacketTests
{
    [Test]
    public async Task ResultBody_MatchesNativeTwentyFourByteLayout()
    {
        var packet = new SCItemReRollEvolvingResultPacket(
            0x0102030405060708,
            2,
            true,
            new SCItemReRollEvolvingResultPacket.EvolvingModifier(77, 1, 1234),
            new SCItemReRollEvolvingResultPacket.EvolvingModifier(82, 0, -567));
        var stream = new PacketStream();

        packet.Write(stream);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(24);
        await Assert.That(BitConverter.ToUInt64(body, 0)).IsEqualTo(0x0102030405060708ul);
        await Assert.That(body[8]).IsEqualTo((byte)2);
        await Assert.That(body[9]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToUInt16(body, 10)).IsEqualTo((ushort)77);
        await Assert.That(body[12]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToInt32(body, 13)).IsEqualTo(1234);
        await Assert.That(BitConverter.ToUInt16(body, 17)).IsEqualTo((ushort)82);
        await Assert.That(body[19]).IsEqualTo((byte)0);
        await Assert.That(BitConverter.ToInt32(body, 20)).IsEqualTo(-567);
    }
}
