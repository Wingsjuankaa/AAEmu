using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCProcessingInstancePacketTests
{
    [Test]
    public async Task Write_UsesZoneAndDynamicInstanceAsNativeStateTuple()
    {
        var stream = new PacketStream();

        new SCProcessingInstancePacket(new ZoneInstanceId(265, 100)).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)265);
        await Assert.That(body.ReadUInt32()).IsEqualTo((uint)100);
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }
}
