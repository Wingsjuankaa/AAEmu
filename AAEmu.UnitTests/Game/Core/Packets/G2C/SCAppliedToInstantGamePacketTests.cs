using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.InstantGame.Static;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCAppliedToInstantGamePacketTests
{
    [Test]
    public async Task Write_UsesInstanceTypeAndErrorWithoutCorps()
    {
        var stream = new PacketStream();

        new SCAppliedToInstantGamePacket(20).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)20);
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)0);
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }
}
