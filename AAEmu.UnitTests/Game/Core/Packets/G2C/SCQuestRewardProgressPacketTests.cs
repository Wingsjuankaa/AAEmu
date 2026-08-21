using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCQuestRewardProgressPacketTests
{
    [Test]
    public async Task FamilyPackets_WriteExactR575FieldWidths()
    {
        var changeStream = new PacketStream();
        new SCFamilyExpChangeNotifyPacket(7, 1234, 3, 45000).Write(changeStream);
        var change = new PacketStream(changeStream.GetBytes());
        await Assert.That(change.ReadInt32()).IsEqualTo(7);
        await Assert.That(change.ReadUInt64()).IsEqualTo(1234ul);
        await Assert.That(change.ReadUInt32()).IsEqualTo(3u);
        await Assert.That(change.ReadUInt32()).IsEqualTo(45000u);
        await Assert.That(change.Pos).IsEqualTo(change.Count);

        var infoSetStream = new PacketStream();
        new SCFamilyInfoSetPacket(7, 3, 12, "family", 2, 1, 123).Write(infoSetStream);
        var infoSet = new PacketStream(infoSetStream.GetBytes());
        await Assert.That(infoSet.ReadInt32()).IsEqualTo(7);
        await Assert.That(infoSet.ReadUInt32()).IsEqualTo(3u);
        await Assert.That(infoSet.ReadUInt32()).IsEqualTo(12u);
        await Assert.That(infoSet.ReadString()).IsEqualTo("family");
        await Assert.That(infoSet.ReadInt32()).IsEqualTo(2);
        await Assert.That(infoSet.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(infoSet.ReadInt64()).IsEqualTo(123L);
        await Assert.That(infoSet.Pos).IsEqualTo(infoSet.Count);

        var dryStream = new PacketStream();
        new SCFamilyExpChangeDryNotifyPacket(100).Write(dryStream);
        var dry = new PacketStream(dryStream.GetBytes());
        await Assert.That(dry.ReadUInt32()).IsEqualTo(100u);
        await Assert.That(dry.Pos).IsEqualTo(dry.Count);
    }

    [Test]
    public async Task ExpeditionExpPacket_WritesUnsignedDelta()
    {
        var stream = new PacketStream();
        new SCExpeditionExpAddPacket(2400).Write(stream);
        var body = new PacketStream(stream.GetBytes());
        await Assert.That(body.ReadUInt32()).IsEqualTo(2400u);
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ResidentPackets_WriteExactR575FieldWidths()
    {
        var infoStream = new PacketStream();
        new SCResidentInfoPacket(33, 1234, 30).Write(infoStream);
        var info = new PacketStream(infoStream.GetBytes());
        await Assert.That(info.ReadInt16()).IsEqualTo((short)33);
        await Assert.That(info.ReadUInt64()).IsEqualTo(1234ul);
        await Assert.That(info.ReadUInt32()).IsEqualTo(30u);
        await Assert.That(info.Pos).IsEqualTo(info.Count);

        var balanceStream = new PacketStream();
        new SCResidentBalanceInfoPacket(33, 1234, 5, 30, 10000, 20, 10).Write(balanceStream);
        var balance = new PacketStream(balanceStream.GetBytes());
        await Assert.That(balance.ReadInt16()).IsEqualTo((short)33);
        await Assert.That(balance.ReadUInt64()).IsEqualTo(1234ul);
        await Assert.That(balance.ReadUInt32()).IsEqualTo(5u);
        await Assert.That(balance.ReadUInt32()).IsEqualTo(30u);
        await Assert.That(balance.ReadUInt32()).IsEqualTo(10000u);
        await Assert.That(balance.ReadUInt64()).IsEqualTo(20ul);
        await Assert.That(balance.ReadUInt64()).IsEqualTo(10ul);
        await Assert.That(balance.Pos).IsEqualTo(balance.Count);
    }

    [Test]
    public async Task FactionChangeDropPacket_WritesNativeBatchesAndCapsAtTwentyIds()
    {
        var stream = new PacketStream();
        var ids = Enumerable.Range(100, 22).Select(id => (uint)id).ToArray();
        new SCDropQuestsByFactionChangePacket(true, ids).Write(stream);

        var body = new PacketStream(stream.GetBytes());
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadUInt32()).IsEqualTo(20u);
        for (uint expected = 100; expected < 120; expected++)
            await Assert.That(body.ReadUInt32()).IsEqualTo(expected);
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }
}
