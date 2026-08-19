using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCBlessUthstinPacketsTests
{
    [Test]
    public async Task ConsumePreview_UsesTheExactR575FieldOrder()
    {
        var body = Write(new SCBlessUthstinConsumeApplyStatsPacket(
            0x010203, true, 42822, 0, 3, 1, 1));

        await Assert.That(SCOffsets.SCBlessUthstinConsumeApplyStatsPacket).IsEqualTo((ushort)0x2EC);
        await Assert.That(body.ReadBc()).IsEqualTo(0x010203u);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadInt32()).IsEqualTo(42822);
        await Assert.That(body.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(3u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }

    [Test]
    public async Task ApplyResult_WritesFiveSignedStatsBeforePageAndCounters()
    {
        var body = Write(new SCBlessUthstinApplyStatsPacket(
            0x010203, true, [10, -10, 3, -3, 0], 2, 4, 5, false));

        await Assert.That(SCOffsets.SCBlessUthstinApplyStatsPacket).IsEqualTo((ushort)0x2ED);
        await Assert.That(body.ReadBc()).IsEqualTo(0x010203u);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(Enumerable.Range(0, 5).Select(_ => body.ReadInt32()).ToArray())
            .IsEquivalentTo(new[] { 10, -10, 3, -3, 0 });
        await Assert.That(body.ReadInt32()).IsEqualTo(2);
        await Assert.That(body.ReadUInt32()).IsEqualTo(4u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(5u);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }

    [Test]
    public async Task CopyAndAboxPackets_WriteAllFiveStats()
    {
        var copy = Write(new SCBlessUthstinCopyPagePacket(
            0x010203, true, 1, [1, 2, 3, 4, 5], 6, 7));
        var abox = Write(new SCAboxBlessUthstinApplyStatsPacket(
            0x010203, true, [-1, -2, -3, -4, -5], 2));

        await Assert.That(copy.GetBytes().Length).IsEqualTo(36);
        await Assert.That(abox.GetBytes().Length).IsEqualTo(28);
    }

    private static PacketStream Write(AAEmu.Game.Core.Network.Game.GamePacket packet)
    {
        var stream = new PacketStream();
        packet.Write(stream);
        return new PacketStream(stream.GetBytes());
    }
}
