using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCRebuildHouseTaxInfoPacketTests
{
    [Test]
    public async Task NativeR575BodyWritesEntriesInExactOrderAndWidths()
    {
        var stream = new PacketStream();
        new SCRebuildHouseTaxInfoPacket(
            0x1234,
            17,
            [new HousingRebuildTaxEntry(150_000, true, -2.5d, 225_000, 9)])
            .Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)0x1234);
        await Assert.That(stream.ReadInt32()).IsEqualTo(17);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(stream.ReadInt32()).IsEqualTo(150_000);
        await Assert.That(stream.ReadBoolean()).IsTrue();
        await Assert.That(stream.ReadDouble()).IsEqualTo(-2.5d);
        await Assert.That(stream.ReadInt32()).IsEqualTo(225_000);
        await Assert.That(stream.ReadInt32()).IsEqualTo(9);
        await Assert.That(stream.HasBytes).IsFalse();
    }

    [Test]
    public async Task NativeR575BodyCapsForgedEntryCountAtOneHundred()
    {
        var entries = Enumerable.Range(0, 101)
            .Select(index => new HousingRebuildTaxEntry(index, true, index, index, index))
            .ToArray();
        var stream = new PacketStream();
        new SCRebuildHouseTaxInfoPacket(1, 0, entries).Write(stream);
        stream.Pos = sizeof(ushort) + sizeof(int);

        await Assert.That(stream.ReadUInt32()).IsEqualTo(100u);
        await Assert.That(stream.GetBytes().Length)
            .IsEqualTo(sizeof(ushort) + sizeof(int) + sizeof(uint) + 100 * 21);
    }
}
