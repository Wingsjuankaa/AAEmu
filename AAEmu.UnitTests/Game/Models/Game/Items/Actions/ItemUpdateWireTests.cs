using System.Buffers.Binary;

using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Actions;

public class ItemUpdateWireTests
{
    [Test]
    public async Task EquipmentUpdateDetail_WritesExactR575InternalUnion()
    {
        var template = new WeaponTemplate
        {
            Id = 60000,
            Level = 55,
            HoldableTemplate = new Holdable { SlotTypeId = 4 }
        };
        var item = new EquipItem(0x0102030405060708, template, 1)
        {
            SlotType = SlotType.Inventory,
            Slot = 9,
            Durability = 77,
            ChargeCount = 513,
            ChargeStartTime = DateTime.UnixEpoch.AddSeconds(123456),
            ScaledA = 0x3344,
            EvolveChance = 0x5566,
            ChargeProcTime = DateTime.UnixEpoch.AddSeconds(654321),
            MappingFailBonus = 0x77,
            ElementLevel = 0x88,
            ImageItemTemplateId = 987654
        };
        for (var index = 0; index < EquipItem.GemDataSlots; index++)
            item.GemData[index] = (uint)(1000 + index);

        var stream = new PacketStream();
        new ItemUpdate(item).Write(stream);
        var body = stream.GetBytes();
        const int detail = 14;

        await Assert.That(body.Length).IsEqualTo(142);
        await Assert.That(body[0]).IsEqualTo((byte)ItemAction.UpdateDetail);
        await Assert.That(body[2]).IsEqualTo((byte)SlotType.Inventory);
        await Assert.That(body[3]).IsEqualTo((byte)9);
        await Assert.That(BinaryPrimitives.ReadUInt64LittleEndian(body.AsSpan(4, 8)))
            .IsEqualTo(0x0102030405060708UL);
        await Assert.That(BinaryPrimitives.ReadUInt16LittleEndian(body.AsSpan(12, 2))).IsEqualTo((ushort)128);

        await Assert.That(body[detail]).IsEqualTo((byte)ItemDetailType.Equipment);
        await Assert.That(ReadUInt32(body, detail + 0x01)).IsEqualTo(987654u);
        await Assert.That(body[detail + 0x05]).IsEqualTo((byte)77);
        await Assert.That(ReadUInt16(body, detail + 0x06)).IsEqualTo((ushort)513);
        await Assert.That(ReadUInt32(body, detail + 0x08)).IsEqualTo(1001u);
        await Assert.That(ReadInt64(body, detail + 0x0C)).IsEqualTo(Helpers.UnixTime(item.ChargeStartTime));
        await Assert.That(ReadUInt32(body, detail + 0x14)).IsEqualTo(1002u);

        for (var index = 0; index < 9; index++)
            await Assert.That(ReadUInt32(body, detail + 0x18 + index * sizeof(uint)))
                .IsEqualTo((uint)(1004 + index));

        await Assert.That(ReadUInt16(body, detail + 0x3C)).IsEqualTo((ushort)0x3344);
        await Assert.That(ReadUInt16(body, detail + 0x3E)).IsEqualTo((ushort)0x5566);
        await Assert.That(ReadUInt32(body, detail + 0x40)).IsEqualTo(1003u);

        for (var index = 0; index < 5; index++)
            await Assert.That(ReadUInt32(body, detail + 0x44 + index * sizeof(uint)))
                .IsEqualTo((uint)(1013 + index));

        await Assert.That(ReadInt64(body, detail + 0x58)).IsEqualTo(Helpers.UnixTime(item.ChargeProcTime));
        await Assert.That(body[detail + 0x60]).IsEqualTo((byte)0x77);
        await Assert.That(body[detail + 0x61]).IsEqualTo((byte)0x88);
        await Assert.That(body.AsSpan(detail + 0x62, 0x1E).ToArray()).IsEquivalentTo(new byte[0x1E]);
    }

    private static ushort ReadUInt16(byte[] body, int offset) =>
        BinaryPrimitives.ReadUInt16LittleEndian(body.AsSpan(offset, sizeof(ushort)));

    private static uint ReadUInt32(byte[] body, int offset) =>
        BinaryPrimitives.ReadUInt32LittleEndian(body.AsSpan(offset, sizeof(uint)));

    private static long ReadInt64(byte[] body, int offset) =>
        BinaryPrimitives.ReadInt64LittleEndian(body.AsSpan(offset, sizeof(long)));
}
