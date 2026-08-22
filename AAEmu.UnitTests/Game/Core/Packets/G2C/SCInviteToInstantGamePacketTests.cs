using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCInviteToInstantGamePacketTests
{
    [Test]
    public async Task Write_UsesNativeR575InvitationLayout()
    {
        var stream = new PacketStream();

        new SCInviteToInstantGamePacket(
            123456,
            new ZoneInstanceId(265, 100),
            0,
            1,
            1,
            5).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadInt32()).IsEqualTo(123456);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)265);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)100);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)0);
        await Assert.That(body.ReadUInt64()).IsEqualTo((ulong)1);
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)2);
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)0);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)1);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)5);
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }
}
