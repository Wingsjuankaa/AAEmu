using System;
using System.Collections.Generic;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
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
            Assert.Equal(193, stream.Count);
            Assert.Equal(42L, BitConverter.ToInt64(stream.GetBytes(), stream.Count - sizeof(long)));
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
    }
}
