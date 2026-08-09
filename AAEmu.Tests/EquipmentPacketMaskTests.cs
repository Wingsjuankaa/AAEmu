using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class EquipmentPacketMaskTests
    {
        [Fact]
        public void ValidFlagsUsePhysicalSlotIndices()
        {
            var items = EmptyEquipment();
            items[0] = new Item();
            items[15] = new Item();
            items[31] = new Item();

            var flags = EquipmentPacketMasks.BuildValidFlags(items);

            Assert.Equal(0x80008001u, flags);
        }

        [Fact]
        public void EmptySlotsAreNotCompactedWhenBuildingItemFlags()
        {
            var items = EmptyEquipment();
            items[15] = new Item { ItemFlags = ItemFlag.SoulBound };
            items[31] = new Item { ItemFlags = ItemFlag.SoulBound };

            var flags = EquipmentPacketMasks.BuildItemFlags(items);

            Assert.Equal(0x80008000u, flags);
        }

        [Fact]
        public void MultiBitItemDetailDoesNotOverlapAdjacentPhysicalSlots()
        {
            var items = EmptyEquipment();
            items[15] = new Item { ItemFlags = ItemFlag.SoulBound | ItemFlag.Secure };

            var flags = EquipmentPacketMasks.BuildItemFlags(items);

            Assert.Equal(1u << 15, flags);
        }

        private static List<Item> EmptyEquipment()
        {
            var items = new List<Item>(EquipmentPacketMasks.PhysicalSlotCount);
            for (var index = 0; index < EquipmentPacketMasks.PhysicalSlotCount; index++)
                items.Add(null);
            return items;
        }
    }
}
