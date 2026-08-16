using System.Buffers.Binary;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemRefurbishmentResultPacketTests
{
    [Test]
    public async Task NativeR575Body_EndsWithReservedBeforeAndAfterScales()
    {
        var item = new Item { Id = 0x0102030405060708 };
        var stream = new PacketStream();

        new SCItemRefurbishmentResultPacket(ItemRefurbishmentResult.GreatSuccess,
            item, 7, 9).Write(stream);
        var body = stream.GetBytes();

        var opcodeField = typeof(SCOffsets).GetField(nameof(SCOffsets.SCItemRefurbishmentResultPacket))!;
        var opcode = (ushort)opcodeField.GetRawConstantValue()!;
        await Assert.That(opcode).IsEqualTo((ushort)0xCC);
        await Assert.That(body[0]).IsEqualTo((byte)ItemRefurbishmentResult.GreatSuccess);
        await Assert.That(BinaryPrimitives.ReadUInt32LittleEndian(body.AsSpan(body.Length - 8, 4)))
            .IsEqualTo(0u);
        await Assert.That(BinaryPrimitives.ReadUInt16LittleEndian(body.AsSpan(body.Length - 4, 2)))
            .IsEqualTo((ushort)7);
        await Assert.That(BinaryPrimitives.ReadUInt16LittleEndian(body.AsSpan(body.Length - 2, 2)))
            .IsEqualTo((ushort)9);
    }
}
