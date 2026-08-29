using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCWorldInteractionSkillListPacketTests
{
    [Test]
    public async Task NativeR575BodyWritesEnvelopeAndNestedInteractionList()
    {
        var stream = new PacketStream();
        new SCWorldInteractionSkillListPacket(
            0x0012_3456,
            0x0000_0789,
            17,
            -1,
            2,
            0x1020_3040,
            [29291]).Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadBc()).IsEqualTo(0x0012_3456u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x0000_0789u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x0000_0789u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x0012_3456u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x00FF_FFFFu);
        await Assert.That(stream.ReadInt32()).IsEqualTo(1);
        await Assert.That(stream.ReadInt32()).IsEqualTo(17);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(29291u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)2);
        await Assert.That(stream.ReadInt32()).IsEqualTo(0x1020_3040);
        await Assert.That(stream.HasBytes).IsFalse();
    }

    [Test]
    public async Task NativeR575BodyCapsInteractionsAtTenAndRejectsWideHandles()
    {
        var stream = new PacketStream();
        new SCWorldInteractionSkillListPacket(
            0x0100_0000,
            0x0200_0000,
            0,
            0,
            0,
            0,
            Enumerable.Range(1, 11).Select(value => (uint)value)).Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadBc()).IsEqualTo(0u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0u);
        await Assert.That(stream.ReadBc()).IsEqualTo(0u);
        stream.ReadUInt32();
        stream.ReadBc();
        await Assert.That(stream.ReadInt32()).IsEqualTo(10);
        stream.ReadInt32();
        for (uint value = 1; value <= 10; value++)
            await Assert.That(stream.ReadUInt32()).IsEqualTo(value);
        stream.ReadByte();
        stream.ReadInt32();
        await Assert.That(stream.HasBytes).IsFalse();
    }
}
