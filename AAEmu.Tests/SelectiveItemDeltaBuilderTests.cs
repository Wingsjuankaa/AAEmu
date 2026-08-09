using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class SelectiveItemDeltaBuilderTests
    {
        [Fact]
        public void ReusedItemIdWithNewTemplateProducesRemoveAndCreate()
        {
            const ulong reusedId = 16777240;
            var before = new Dictionary<ulong, SelectiveItemSnapshot>
            {
                [reusedId] = new SelectiveItemSnapshot
                {
                    Id = reusedId,
                    SlotType = SlotType.Inventory,
                    Slot = 7,
                    TemplateId = 47869,
                    Count = 1
                }
            };
            var result = new Item
            {
                Id = reusedId,
                SlotType = SlotType.Inventory,
                Slot = 7,
                TemplateId = 45862,
                Count = 1
            };
            var after = new Dictionary<ulong, Item>
            {
                [reusedId] = result
            };

            var tasks = SelectiveItemDeltaBuilder.Build(before, after);

            Assert.Collection(
                tasks,
                task => Assert.Equal(ItemAction.Remove, task.Type),
                task => Assert.Equal(ItemAction.Create, task.Type));
        }

        [Fact]
        public void SameInventoryIdentityUsesCountDeltaOnly()
        {
            const ulong itemId = 16777241;
            var before = new Dictionary<ulong, SelectiveItemSnapshot>
            {
                [itemId] = new SelectiveItemSnapshot
                {
                    Id = itemId,
                    SlotType = SlotType.Inventory,
                    Slot = 8,
                    TemplateId = 45862,
                    Count = 1
                }
            };
            var current = new Item
            {
                Id = itemId,
                SlotType = SlotType.Inventory,
                Slot = 8,
                TemplateId = 45862,
                Count = 2
            };
            var after = new Dictionary<ulong, Item>
            {
                [itemId] = current
            };

            var tasks = SelectiveItemDeltaBuilder.Build(before, after);

            var task = Assert.Single(tasks);
            Assert.Equal(ItemAction.AddStack, task.Type);
        }
    }
}
