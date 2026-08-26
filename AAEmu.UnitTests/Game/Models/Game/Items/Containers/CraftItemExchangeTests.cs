using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Containers;

[NotInParallel]
public class CraftItemExchangeTests
{
    private object _oldItemManager;

    [Before(Test)]
    public void InstallItemManager()
    {
        var singletonField = typeof(Singleton<ItemManager>).GetField(
            "s_instance", BindingFlags.Static | BindingFlags.NonPublic);
        _oldItemManager = singletonField.GetValue(null);

        var manager = new ItemManager(
            null, Mock.Of<IItemIdManager>().Object, null, null, null, null);
        SetPrivateField(manager, "_templates", new Dictionary<uint, ItemTemplate>
        {
            [10] = new() { Id = 10, MaxCount = 10, FixedGrade = 0 },
            [20] = new() { Id = 20, MaxCount = 1, FixedGrade = 0 }
        });
        SetPrivateField(manager, "_allItems", new Dictionary<ulong, Item>());
        SetPrivateField(manager, "_removedItems", new List<ulong>());
        singletonField.SetValue(null, manager);
    }

    [After(Test)]
    public void RestoreItemManager()
    {
        typeof(Singleton<ItemManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)
            .SetValue(null, _oldItemManager);
    }

    [Test]
    public async Task CommitsConsumptionAndRewardAsOneExchange()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 3));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2)],
            [new CraftProductGrant(10, 2, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(3);
        await Assert.That(consumeTasks.Count).IsEqualTo(1);
        await Assert.That(rewardTasks.Count).IsEqualTo(1);
        await Assert.That(removals).IsEmpty();
    }

    [Test]
    public async Task MissingMaterialLeavesInventoryAndTaskBatchesUntouched()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 1));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2)],
            [new CraftProductGrant(10, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.MissingMaterials);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(1);
        await Assert.That(consumeTasks).IsEmpty();
        await Assert.That(rewardTasks).IsEmpty();
        await Assert.That(removals).IsEmpty();
    }

    [Test]
    public async Task ConsumesOneRequirementAcrossMultipleStacks()
    {
        var template = new ItemTemplate { Id = 10, MaxCount = 10, FixedGrade = 0 };
        var bag = CreateBag(
            new ItemMock(1, template, 1),
            new ItemMock(2, template, 3));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 3)],
            [new CraftProductGrant(10, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items).Count().IsEqualTo(1);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(2);
        await Assert.That(consumeTasks).Count().IsEqualTo(2);
        await Assert.That(rewardTasks).Count().IsEqualTo(1);
        await Assert.That(removals).Contains(1ul);
    }

    [Test]
    public async Task FullBagLeavesMaterialsUntouched()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 3));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2)],
            [new CraftProductGrant(20, 1, 0)]);

        var ok = bag.TryExchangeCraftItems(
            plan, 7, [], [], [], out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.BagFull);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(3);
    }

    [Test]
    public async Task NonDestroyableMaterialLeavesInventoryUntouched()
    {
        var template = new ItemTemplate { Id = 10, MaxCount = 10, FixedGrade = 0 };
        var bag = CreateBag(new NonDestroyableItem(1, template, 2));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2)],
            [new CraftProductGrant(10, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.ItemNotDestroyable);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(2);
        await Assert.That(consumeTasks).IsEmpty();
        await Assert.That(rewardTasks).IsEmpty();
        await Assert.That(removals).IsEmpty();
    }

    private static ItemContainer CreateBag(params Item[] items)
    {
        var character = new CharacterMock();
        var bag = new ItemContainer(0, SlotType.Inventory, false, character)
        {
            ContainerSize = (byte)items.Length
        };
        for (var index = 0; index < items.Length; index++)
        {
            var item = items[index];
            item.SlotType = SlotType.Inventory;
            item.Slot = (byte)index;
            item.OwnerId = 0;
            item._holdingContainer = bag;
            bag.Items.Add(item);
        }
        bag.UpdateFreeSlotCount();
        return bag;
    }

    private static void SetPrivateField(object target, string fieldName, object value) =>
        target.GetType().GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic)
            .SetValue(target, value);

    private sealed class NonDestroyableItem(uint id, ItemTemplate template, int count)
        : ItemMock(id, template, count)
    {
        public override bool CanDestroy() => false;
    }
}
