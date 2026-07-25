using System;
using System.Collections.Generic;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Tests.Utils;
using Xunit;

namespace AAEmu.Tests
{
    public class ItemTaskSerializationTests
    {
        [Fact]
        public void MoneyChangeUsesUpdateOnlyLogType()
        {
            var stream = new PacketStream();
            new MoneyChange(15000).Write(stream);

            Assert.Equal(new byte[] { 1, 0, 0x98, 0x3A, 0, 0, 0, 0, 0, 0 }, stream.GetBytes());
        }

        [Theory]
        [InlineData(25, ItemTaskLogType.MoveItem)]
        [InlineData(-25, ItemTaskLogType.RemoveItem)]
        [InlineData(0, ItemTaskLogType.UpdateOnly)]
        public void StackChangesUseDirectionAwareLogType(int amount, ItemTaskLogType expectedLogType)
        {
            var item = InventoryTestUtils.MockItem(77, 123);
            item.SlotType = SlotType.Inventory;
            item.Slot = 4;

            var stream = new PacketStream();
            new ItemCountUpdate(item, amount).Write(stream);

            Assert.Equal((byte)ItemAction.AddStack, stream[0]);
            Assert.Equal(5, stream[0]);
            Assert.Equal((byte)expectedLogType, stream[1]);
            Assert.Equal((byte)SlotType.Inventory, stream[2]);
            Assert.Equal(4, stream[3]);
            Assert.Equal(item.Id, BitConverter.ToUInt64(stream.GetBytes(), 4));
            Assert.Equal(amount, BitConverter.ToInt32(stream.GetBytes(), 12));
            Assert.Equal(item.TemplateId, BitConverter.ToUInt32(stream.GetBytes(), 16));
            Assert.Equal(20, stream.Count);
        }

        [Fact]
        public void EightZeroItemActionsIncludeInsertedTypedPointAction()
        {
            Assert.Equal(4, (int)ItemAction.ChangeTypedPoint);
            Assert.Equal(5, (int)ItemAction.AddStack);
            Assert.Equal(6, (int)ItemAction.Create);
            Assert.Equal(8, (int)ItemAction.Remove);
            Assert.Equal(20, (int)ItemAction.UpdateChargeUseSkillTime);
        }

        [Theory]
        [InlineData(1)]
        [InlineData(-1)]
        public void LongCurrencyActionsUseEightByteAmounts(long amount)
        {
            var bankMoney = new PacketStream();
            new MoneyChangeBank(amount).Write(bankMoney);
            Assert.Equal(10, bankMoney.Count);
            Assert.Equal(amount, BitConverter.ToInt64(bankMoney.GetBytes(), 2));

            var aaPoint = new PacketStream();
            new AAPointUpdate(amount).Write(aaPoint);
            Assert.Equal(10, aaPoint.Count);
            Assert.Equal(amount, BitConverter.ToInt64(aaPoint.GetBytes(), 2));
        }

        [Fact]
        public void MovesDistinguishSwapFromCrossContainerMove()
        {
            var swap = new PacketStream();
            new ItemMove(SlotType.Inventory, 1, 10, SlotType.Inventory, 2, 20).Write(swap);
            Assert.Equal((byte)ItemTaskLogType.SwapItem, swap[1]);

            var move = new PacketStream();
            new ItemMove(SlotType.Inventory, 1, 10, SlotType.Bank, 2, 20).Write(move);
            Assert.Equal((byte)ItemTaskLogType.MoveItem, move[1]);
        }

        [Fact]
        public void ItemAddWritesCompleteEightZeroPayload()
        {
            var item = InventoryTestUtils.MockItem(77, 123);
            item.SlotType = SlotType.Inventory;
            item.Slot = 4;
            item.ChargeUseSkillTime = new DateTime(1970, 1, 1, 0, 0, 42, DateTimeKind.Utc);

            var stream = new PacketStream();
            new ItemAdd(item).Write(stream);

            Assert.Equal((byte)ItemAction.Create, stream[0]);
            Assert.Equal((byte)ItemTaskLogType.GainItem, stream[1]);
            Assert.Equal(64, stream.Count);
            Assert.Equal(42L, BitConverter.ToInt64(stream.GetBytes(), stream.Count - sizeof(long)));
        }

        [Fact]
        public void SnapshotAndIncrementalCreateUseTheSameItemPayload()
        {
            var item = InventoryTestUtils.MockItem(77, 123);
            item.ItemFlags = ItemFlag.SoulBound | ItemFlag.Secure;
            item.SlotType = SlotType.Inventory;
            item.Slot = 4;

            var snapshot = new PacketStream();
            item.Write(snapshot);
            var incremental = new PacketStream();
            new ItemAdd(item).Write(incremental);

            Assert.Equal(snapshot.GetBytes(), incremental.GetBytes()[4..]);
        }

        [Fact]
        public void IncrementalEquipmentCreateWritesDetailTypeAndDurabilityWithoutLengthPrefix()
        {
            var template = new EquipItemTemplate
            {
                Id = 45634,
                BindType = ItemBindType.Normal
            };
            var item = new EquipItem(77, template, 1)
            {
                SlotType = SlotType.Inventory,
                Slot = 4,
                Grade = 4,
                Durability = 145
            };

            var stream = new PacketStream();
            new ItemAdd(item).Write(stream);

            Assert.Equal((byte)ItemDetailType.Equipment, stream[22]);
            Assert.Equal(145, stream[23]);
        }

        [Fact]
        public void ItemUpdateWritesAa8InternalEquipmentDetailBlock()
        {
            var template = new EquipItemTemplate
            {
                Id = 45634,
                BindType = ItemBindType.Normal
            };
            var item = new EquipItem(77, template, 1)
            {
                SlotType = SlotType.Inventory,
                Slot = 4,
                Grade = 4,
                Durability = 145,
                ChargeCount = 7,
                ChargeTime = new DateTime(1970, 1, 1, 0, 2, 3, DateTimeKind.Utc),
                ScaledA = 4,
                EvolveChance = 321,
                ChargeProcTime = new DateTime(1970, 1, 1, 0, 7, 36, DateTimeKind.Utc),
                MappingFailBonus = 8,
                ElementLevel = 9
            };
            for (var index = 0; index < item.GemIds.Length; index++)
                item.GemIds[index] = (uint)(1000 + index);

            var stream = new PacketStream();
            new ItemUpdate(item).Write(stream);
            var bytes = stream.GetBytes();
            const int detailOffset = 14;

            Assert.Equal((byte)ItemAction.UpdateDetail, stream[0]);
            Assert.Equal((byte)ItemTaskLogType.UpdateOnly, stream[1]);
            Assert.Equal((byte)SlotType.Inventory, stream[2]);
            Assert.Equal(4, stream[3]);
            Assert.Equal(item.Id, BitConverter.ToUInt64(bytes, 4));
            Assert.Equal(128, BitConverter.ToUInt16(bytes, 12));
            Assert.Equal((byte)ItemDetailType.Equipment, bytes[detailOffset]);
            Assert.Equal(item.GemIds[0], BitConverter.ToUInt32(bytes, detailOffset + 0x01));
            Assert.Equal(145, bytes[detailOffset + 0x05]);
            Assert.Equal(7, BitConverter.ToInt16(bytes, detailOffset + 0x06));
            Assert.Equal(item.GemIds[1], BitConverter.ToUInt32(bytes, detailOffset + 0x08));
            Assert.Equal(123L, BitConverter.ToInt64(bytes, detailOffset + 0x0C));
            Assert.Equal(item.GemIds[2], BitConverter.ToUInt32(bytes, detailOffset + 0x14));
            Assert.Equal(item.GemIds[4], BitConverter.ToUInt32(bytes, detailOffset + 0x18));
            Assert.Equal(item.GemIds[12], BitConverter.ToUInt32(bytes, detailOffset + 0x38));
            Assert.Equal((ushort)4, BitConverter.ToUInt16(bytes, detailOffset + 0x3C));
            Assert.Equal((ushort)321, BitConverter.ToUInt16(bytes, detailOffset + 0x3E));
            Assert.Equal(item.GemIds[3], BitConverter.ToUInt32(bytes, detailOffset + 0x40));
            Assert.Equal(item.GemIds[13], BitConverter.ToUInt32(bytes, detailOffset + 0x44));
            Assert.Equal(item.GemIds[17], BitConverter.ToUInt32(bytes, detailOffset + 0x54));
            Assert.Equal(456L, BitConverter.ToInt64(bytes, detailOffset + 0x58));
            Assert.Equal(8, bytes[detailOffset + 0x60]);
            Assert.Equal(9, bytes[detailOffset + 0x61]);
            Assert.Equal(14 + 128, stream.Count);
        }

        [Fact]
        public void SuccessPacketWritesOwnerTypeCountsAndTrailer()
        {
            var packet = new SCItemTaskSuccessPacket(ItemTaskType.Gm,
                new List<ItemTask> { new MoneyChange(15000) }, null,
                type: 7, lockItemSlotKey: 8, unitOwnerType: 0, flags: 9);
            var stream = new PacketStream();

            packet.Write(stream);

            Assert.Equal(26, stream.Count);
            Assert.Equal(0, stream[0]);
            Assert.Equal((byte)ItemTaskType.Gm, stream[1]);
            Assert.Equal(1, stream[2]);
            Assert.Equal(15000L, BitConverter.ToInt64(stream.GetBytes(), 5));
            Assert.Equal(0, stream[13]);
            Assert.Equal(7u, BitConverter.ToUInt32(stream.GetBytes(), 14));
            Assert.Equal(8u, BitConverter.ToUInt32(stream.GetBytes(), 18));
            Assert.Equal(9u, BitConverter.ToUInt32(stream.GetBytes(), 22));
        }

        [Fact]
        public void RefurbishmentUsesAa8NativeScaleCapTaskReason()
        {
            var item = InventoryTestUtils.MockItem(77, 123);
            var packet = new SCItemTaskSuccessPacket(
                ItemTaskType.Refurbishment,
                new ItemUpdate(item),
                new List<ulong>());
            var stream = new PacketStream();

            packet.Write(stream);

            Assert.Equal(0x7F, (byte)ItemTaskType.Refurbishment);
            Assert.Equal(0x7F, stream[1]);
        }

        [Fact]
        public void RefurbishmentResultMatchesAa8ClientWireLayout()
        {
            var item = InventoryTestUtils.MockItem(77, 123);
            var packet = new SCItemRefurbishmentResultPacket(
                ItemRefurbishmentResult.GreatSuccess,
                item,
                10,
                12);
            var itemStream = new PacketStream();
            var stream = new PacketStream();

            item.Write(itemStream);
            packet.Write(stream);

            var bytes = stream.GetBytes();
            var itemBytes = itemStream.GetBytes();

            Assert.Equal((byte)ItemRefurbishmentResult.GreatSuccess, bytes[0]);
            for (var i = 0; i < itemBytes.Length; i++)
                Assert.Equal(itemBytes[i], bytes[i + 1]);
            Assert.Equal(0u, BitConverter.ToUInt32(bytes, 1 + itemBytes.Length));
            Assert.Equal((ushort)10, BitConverter.ToUInt16(
                bytes, 1 + itemBytes.Length + sizeof(uint)));
            Assert.Equal((ushort)12, BitConverter.ToUInt16(
                bytes, 1 + itemBytes.Length + sizeof(uint) + sizeof(ushort)));
            Assert.Equal(
                1 + itemBytes.Length + sizeof(uint) + sizeof(ushort) * 2,
                stream.Count);
        }

        [Fact]
        public void EvolvingResultMatchesAa8ClientWireLayout()
        {
            var packet = new SCEvolvingResultPacket(
                0x0102030405060708,
                3,
                5,
                400,
                200,
                0,
                new List<EvolvingModifierResult>
                {
                    new()
                    {
                        UnitAttributeId = 77,
                        UnitModifierTypeId = 5,
                        Value = 1234
                    }
                });
            var stream = new PacketStream();

            packet.Write(stream);

            Assert.Equal(
                new byte[]
                {
                    0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01,
                    0x05, 0x03, 0x01,
                    0x90, 0x01, 0x00, 0x00,
                    0xC8, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00,
                    0x4D, 0x00, 0x05,
                    0xD2, 0x04, 0x00, 0x00
                },
                stream.GetBytes());
        }

        [Fact]
        public void AwakeningResultMatchesAa8ClientWireLayout()
        {
            var before = InventoryTestUtils.MockItem(77, 45635);
            before.Grade = 8;
            before.MappingFailBonus = 5;
            var after = InventoryTestUtils.MockItem(77, 45828);
            after.Grade = 8;
            after.MappingFailBonus = 0;
            var beforeStream = new PacketStream();
            var afterStream = new PacketStream();
            var stream = new PacketStream();

            before.Write(beforeStream);
            after.Write(afterStream);
            new SCItemChangeMappingResultPacket(
                    before,
                    after,
                    ItemChangeMappingResult.Success,
                    9)
                .Write(stream);

            var bytes = stream.GetBytes();
            var beforeBytes = beforeStream.GetBytes();
            var afterBytes = afterStream.GetBytes();
            Assert.Equal(
                beforeBytes,
                bytes[..beforeBytes.Length]);
            Assert.Equal(
                afterBytes,
                bytes[
                    beforeBytes.Length..
                    (beforeBytes.Length + afterBytes.Length)]);
            var trailer = beforeBytes.Length + afterBytes.Length;
            Assert.Equal(
                (byte)ItemChangeMappingResult.Success,
                bytes[trailer]);
            Assert.Equal(9u, BitConverter.ToUInt32(bytes, trailer + 1));
            Assert.Equal(trailer + 5, stream.Count);
        }
    }
}
