using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCGachaLootPacketsTests
{
    [Test]
    public async Task Log_UsesNativeByteCountAndNineByteWireRows()
    {
        var stream = Write(new SCGachaLootPackItemLogPacket([
            new GachaLootLogEntry(0x11223344, 7, 25),
            new GachaLootLogEntry(0x55667788, 3, 2)
        ]));

        await Assert.That(SCOffsets.SCGachaLootPackItemLogPacket).IsEqualTo((ushort)0x2E2);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)2);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0x11223344u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)7);
        await Assert.That(stream.ReadInt32()).IsEqualTo(25);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0x55667788u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)3);
        await Assert.That(stream.ReadInt32()).IsEqualTo(2);
        await Assert.That(stream.LeftBytes).IsEqualTo(0);
    }

    [Test]
    public async Task EmptySuccessAndError_UseNativeConditionalBodies()
    {
        var success = Write(new SCGachaLootPackItemResultPacket(
            ErrorMessageType.NoErrorMessage, 0, true, []));
        var error = Write(new SCGachaLootPackItemResultPacket(
            ErrorMessageType.BagFull, 0, true, []));

        await Assert.That(SCOffsets.SCGachaLootPackItemResultPacket).IsEqualTo((ushort)0x2E3);
        await Assert.That(success.ReadInt16()).IsEqualTo((short)0);
        await Assert.That(success.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(success.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(success.ReadBoolean()).IsTrue();
        await Assert.That(success.LeftBytes).IsEqualTo(0);
        await Assert.That(error.ReadInt16()).IsEqualTo((short)ErrorMessageType.BagFull);
        await Assert.That(error.LeftBytes).IsEqualTo(0);
    }

    [Test]
    public async Task BatchResults_CountDownRemainingRoundsToZero()
    {
        var remainingCounts = new uint[] { 2, 1, 0 };

        foreach (var remaining in remainingCounts)
        {
            var stream = Write(new SCGachaLootPackItemResultPacket(
                ErrorMessageType.NoErrorMessage, remaining, true, []));
            await Assert.That(stream.ReadInt16()).IsEqualTo((short)0);
            await Assert.That(stream.ReadUInt32()).IsEqualTo(remaining);
            await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
            await Assert.That(stream.ReadBoolean()).IsTrue();
            await Assert.That(stream.LeftBytes).IsEqualTo(0);
        }
    }

    [Test]
    public async Task Dump_WritesCountThenPackTotalAndRecordPairs()
    {
        var stream = Write(new SCDumpGachaRecordPacket(3, 42, [
            new GachaAdvancedRecordEntry(7, 40),
            new GachaAdvancedRecordEntry(8, 12)
        ]));

        await Assert.That(SCOffsets.SCDumpGachaRecordPacket).IsEqualTo((ushort)0x2E4);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(2u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(3u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(42u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(7u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(40u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(8u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(12u);
        await Assert.That(stream.LeftBytes).IsEqualTo(0);
    }

    private static PacketStream Write(GamePacket packet)
    {
        var stream = new PacketStream();
        packet.Write(stream);
        return new PacketStream(stream.GetBytes());
    }
}
