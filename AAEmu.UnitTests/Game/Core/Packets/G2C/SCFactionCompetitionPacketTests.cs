using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.FactionCompetition;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCFactionCompetitionPacketTests
{
    [Test]
    public async Task PointListWritesExactR575Layout()
    {
        var start = new DateTime(2026, 8, 20, 12, 30, 0, DateTimeKind.Utc);
        var stream = new PacketStream();
        new SCFactionCompetitionPointListPacket(true, 17, start, 2400,
            [new(1, 80), new(2, 100)]).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)17);
        await Assert.That(body.ReadInt64()).IsEqualTo(Helpers.UnixTime(start));
        await Assert.That(body.ReadInt64()).IsEqualTo(2400L);
        await Assert.That(body.ReadInt32()).IsEqualTo(2);
        await Assert.That(body.ReadInt32()).IsEqualTo(1);
        await Assert.That(body.ReadUInt32()).IsEqualTo(80u);
        await Assert.That(body.ReadInt32()).IsEqualTo(2);
        await Assert.That(body.ReadUInt32()).IsEqualTo(100u);
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ResultAndUpdateWriteExactR575Widths()
    {
        var resultStream = new PacketStream();
        new SCFactionCompetitionResultPacket(20, 2, [new(2, 150)]).Write(resultStream);
        var result = new PacketStream(resultStream.GetBytes());
        await Assert.That(result.ReadUInt16()).IsEqualTo((ushort)20);
        await Assert.That(result.ReadInt32()).IsEqualTo(2);
        await Assert.That(result.ReadInt32()).IsEqualTo(1);
        await Assert.That(result.ReadInt32()).IsEqualTo(2);
        await Assert.That(result.ReadUInt32()).IsEqualTo(150u);
        await Assert.That(result.Pos).IsEqualTo(result.Count);

        var updateStream = new PacketStream();
        new SCFactionCompetitionUpdatePointPacket(20, 2, 151).Write(updateStream);
        var update = new PacketStream(updateStream.GetBytes());
        await Assert.That(update.ReadInt16()).IsEqualTo((short)20);
        await Assert.That(update.ReadInt32()).IsEqualTo(2);
        await Assert.That(update.ReadUInt32()).IsEqualTo(151u);
        await Assert.That(update.Pos).IsEqualTo(update.Count);
    }
}
