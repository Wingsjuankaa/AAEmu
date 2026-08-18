using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCExpertLimitModifiedPacketTests
{
    [Test]
    public async Task NativeR575Body_WritesUpgradeAndCompleteCompressedActabilityState()
    {
        var stream = new PacketStream();

        new SCExpertLimitModifiedPacket(true, 1, 20_000, 2).Write(stream);

        await Assert.That(stream.GetBytes()).IsEquivalentTo(
            new byte[] { 1, 4, 1, 0x20, 0x4E, 2 });
    }

    [Test]
    public async Task NativeR575Body_RoundTripsIdPointAndStepInOrder()
    {
        var stream = new PacketStream();
        new SCExpertLimitModifiedPacket(false, 0x0102, 0x010203, 7).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.ReadPisc(2)).IsEquivalentTo(new uint[] { 0x0102, 0x010203 });
        await Assert.That(body.ReadByte()).IsEqualTo((byte)7);
        await Assert.That(body.HasBytes).IsFalse();
    }
}
