using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.InstantGame.Static;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCAppliedToInstantGamePacketTests
{
    [Test]
    public async Task Write_UsesUnifiedInstanceIdBeforeCorpsAndError()
    {
        var stream = new PacketStream();

        new SCAppliedToInstantGamePacket(20, InstantCorps.Corps1).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)20);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)InstantCorps.Corps1);
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)0);
    }
}
