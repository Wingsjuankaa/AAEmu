using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemSocketingLunagemResultPacketTests
{
    [Test]
    public async Task ResultBody_MatchesR575NativeSerializer()
    {
        var packet = new SCItemSocketingLunagemResultPacket(
            1,
            0x0102030405060708ul,
            43500,
            true);
        var stream = new PacketStream();

        packet.Write(stream);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(14);
        await Assert.That(body[0]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToUInt64(body, 1)).IsEqualTo(0x0102030405060708ul);
        await Assert.That(BitConverter.ToUInt32(body, 9)).IsEqualTo(43500u);
        await Assert.That(body[13]).IsEqualTo((byte)1);
    }
}
