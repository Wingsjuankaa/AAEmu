using System.Buffers.Binary;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemSmeltingResultPacketTests
{
    [Test]
    public async Task NativeR575Body_HasNoHistoricalLeadingByte()
    {
        var stream = new PacketStream();
        new SCItemSmeltingResultPacket(
            (sbyte)ItemSmeltingResult.GreatSuccess,
            false,
            0x0102030405060708,
            43445).Write(stream);
        var body = stream.GetBytes();

        await Assert.That(SCOffsets.SCItemSmeltingResultPacket).IsEqualTo((ushort)0xCF);
        await Assert.That(body.Length).IsEqualTo(14);
        await Assert.That(body[0]).IsEqualTo((byte)ItemSmeltingResult.GreatSuccess);
        await Assert.That(body[1]).IsEqualTo((byte)0);
        await Assert.That(BinaryPrimitives.ReadInt64LittleEndian(body.AsSpan(2, 8)))
            .IsEqualTo(0x0102030405060708L);
        await Assert.That(BinaryPrimitives.ReadInt32LittleEndian(body.AsSpan(10, 4)))
            .IsEqualTo(43445);
    }
}
