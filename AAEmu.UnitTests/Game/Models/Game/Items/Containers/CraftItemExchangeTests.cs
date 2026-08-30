using System.Reflection;
using System.Runtime.CompilerServices;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Char;
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
            [20] = new() { Id = 20, MaxCount = 1, FixedGrade = 0 },
            [22] = new BackpackTemplate
            {
                Id = 22, MaxCount = 1, FixedGrade = 0,
                BindType = ItemBindType.BindOnPickup, BackpackType = BackpackType.TradePack
            },
            [23] = new BackpackTemplate
            {
                Id = 23, MaxCount = 1, FixedGrade = 0,
                BindType = ItemBindType.BindOnPickup, BackpackType = BackpackType.Glider
            }
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
            [new CraftMaterialRequirement(10, 2, 0)],
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
        await Assert.That(consumeTasks.Single()).IsTypeOf<ItemCountDecrease>();
        await Assert.That(rewardTasks.Count).IsEqualTo(1);
        await Assert.That(rewardTasks.Single()).IsTypeOf<ItemCountIncrease>();
        await Assert.That(removals).IsEmpty();
    }

    [Test]
    public async Task IntentionalMaterialFreePlanGrantsRewardWithoutConsumeTasks()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 1));
        var plan = new CraftTransactionPlan(9267, [], [new CraftProductGrant(10, 1, 0)])
        {
            AllowsEmptyMaterials = true
        };
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, [], rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(2);
        await Assert.That(consumeTasks).IsEmpty();
        await Assert.That(rewardTasks).Count().IsEqualTo(1);
    }

    [Test]
    public async Task UnclassifiedMaterialFreePlanFailsClosed()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 1));
        var plan = new CraftTransactionPlan(1, [], [new CraftProductGrant(10, 1, 0)]);

        var ok = bag.TryExchangeCraftItems(plan, 7, [], [], [], out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.ConcurrentChange);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(1);
    }

    [Test]
    public async Task MissingMaterialLeavesInventoryAndTaskBatchesUntouched()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 1));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2, 0)],
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
            [new CraftMaterialRequirement(10, 3, 0)],
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
            [new CraftMaterialRequirement(10, 2, 0)],
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
            [new CraftMaterialRequirement(10, 2, 0)],
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

    [Test]
    public async Task GradeAwareExchangeConsumesOnlyThePlannedGrade()
    {
        var template = new ItemTemplate { Id = 10, MaxCount = 10, FixedGrade = 0, Gradable = true };
        var low = new ItemMock(1, template, 2) { Grade = 2 };
        var high = new ItemMock(2, template, 2) { Grade = 5 };
        var bag = CreateBag(low, high);
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2, 5)],
            [new CraftProductGrant(20, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Any(item => item.Id == low.Id && item.Count == 2)).IsTrue();
        await Assert.That(bag.Items.Any(item => item.Id == high.Id)).IsFalse();
        await Assert.That(removals).Contains(high.Id);
    }

    [Test]
    public async Task MainGradeCraftProductPreservesExplicitGradeOnNonGradableTemplate()
    {
        var materialTemplate = new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0, Gradable = true
        };
        var material = new ItemMock(1, materialTemplate, 2) { Grade = 7 };
        var bag = CreateBag(material);
        var plan = new CraftTransactionPlan(11031,
            [new CraftMaterialRequirement(10, 2, 7, true)],
            [new CraftProductGrant(20, 1, 7)]);
        var rewardTasks = new List<ItemTask>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, [], [], rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Single().TemplateId).IsEqualTo(20u);
        await Assert.That(bag.Items.Single().Grade).IsEqualTo((byte)7);
        await Assert.That(rewardTasks).Count().IsEqualTo(1);
    }

    [Test]
    public async Task FailedRateOutcomeStillCommitsMaterialsWithoutCreatingAProduct()
    {
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, 3));
        var plan = new CraftTransactionPlan(1,
            [new CraftMaterialRequirement(10, 2, 0)],
            [])
        {
            FailedProductItemIds = [20]
        };
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, consumeTasks, removals, rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(1);
        await Assert.That(consumeTasks).Count().IsEqualTo(1);
        await Assert.That(rewardTasks).IsEmpty();
    }

    [Test]
    public async Task CraftPaymentAndItemsCommitTogether()
    {
        var character = CreateCharacterWithBag(3, money: 10);
        var plan = new CraftTransactionPlan(
            1, 10, 0, 0, true, 1000,
            [new CraftMaterialRequirement(10, 2, 0)],
            [new CraftProductGrant(10, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = character.TryCommitCraftTransaction(
            plan, 0, 0, consumeTasks, removals, rewardTasks, out var moneyTask, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(character.Money).IsEqualTo(0L);
        await Assert.That(character.Inventory.Bag.Items.Single().Count).IsEqualTo(2);
        await Assert.That(moneyTask).IsTypeOf<MoneyChange>();
        await Assert.That(consumeTasks).Count().IsEqualTo(1);
        await Assert.That(rewardTasks).Count().IsEqualTo(1);
    }

    [Test]
    public async Task InsufficientCraftPaymentLeavesItemsAndTaskBatchesUntouched()
    {
        var character = CreateCharacterWithBag(3, money: 9);
        var plan = new CraftTransactionPlan(
            1, 10, 0, 0, true, 1000,
            [new CraftMaterialRequirement(10, 2, 0)],
            [new CraftProductGrant(10, 1, 0)]);
        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var removals = new List<ulong>();

        var ok = character.TryCommitCraftTransaction(
            plan, 0, 0, consumeTasks, removals, rewardTasks, out var moneyTask, out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.NotEnoughMoney);
        await Assert.That(character.Money).IsEqualTo(9L);
        await Assert.That(character.Inventory.Bag.Items.Single().Count).IsEqualTo(3);
        await Assert.That(moneyTask).IsNull();
        await Assert.That(consumeTasks).IsEmpty();
        await Assert.That(rewardTasks).IsEmpty();
        await Assert.That(removals).IsEmpty();
    }

    [Test]
    public async Task AutoEquipCraftCommitsTradepackWithCrafterAndCreationTime()
    {
        var character = new CharacterMock();
        var bag = CreateBagFor(character, new ItemMock(1, Template(10), 2));
        var equipment = CreateEquipment(character);
        var plan = AutoEquipPlan();
        var rewardTasks = new List<ItemTask>();

        var ok = bag.TryExchangeCraftItems(
            plan, 7, equipment, false, [], [], rewardTasks, out var failure);

        var tradepack = equipment.GetItemBySlot((int)EquipmentItemSlot.Backpack);
        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items).IsEmpty();
        await Assert.That(tradepack).IsNotNull();
        await Assert.That(tradepack.TemplateId).IsEqualTo(22u);
        await Assert.That(tradepack.MadeUnitId).IsEqualTo(7u);
        await Assert.That(tradepack.CreateTime).IsGreaterThan(DateTime.MinValue);
        await Assert.That(rewardTasks).Count().IsEqualTo(1);
    }

    [Test]
    public async Task OccupiedBackpackAndGlidingRejectWithoutPartialMutation()
    {
        var character = new CharacterMock();
        var bag = CreateBagFor(character, new ItemMock(1, Template(10), 2));
        var equipment = CreateEquipment(character, BackpackItem(2, 22));

        var occupied = bag.TryExchangeCraftItems(
            AutoEquipPlan(), 7, equipment, false, [], [], [], out var occupiedFailure);
        equipment.Items.Clear();
        equipment.UpdateFreeSlotCount();
        var gliding = bag.TryExchangeCraftItems(
            AutoEquipPlan(), 7, equipment, true, [], [], [], out var glidingFailure);

        await Assert.That(occupied).IsFalse();
        await Assert.That(occupiedFailure.Code).IsEqualTo(CraftFailureCode.BackpackOccupied);
        await Assert.That(gliding).IsFalse();
        await Assert.That(glidingFailure.Code)
            .IsEqualTo(CraftFailureCode.CannotChangeBackpackInGliding);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(2);
    }

    [Test]
    public async Task EquippedGliderMovesIntoSlotReleasedByConsumptionBeforeTradepackEquip()
    {
        var character = new CharacterMock();
        var bag = CreateBagFor(character, new ItemMock(1, Template(10), 2));
        var glider = BackpackItem(2, 23);
        var equipment = CreateEquipment(character, glider);
        var rewardTasks = new List<ItemTask>();

        var ok = bag.TryExchangeCraftItems(
            AutoEquipPlan(), 7, equipment, false, [], [], rewardTasks, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(bag.Items.Single()).IsSameReferenceAs(glider);
        await Assert.That(glider.SlotType).IsEqualTo(SlotType.Inventory);
        await Assert.That(equipment.GetItemBySlot((int)EquipmentItemSlot.Backpack).TemplateId)
            .IsEqualTo(22u);
        await Assert.That(rewardTasks).Count().IsEqualTo(3);
    }

    [Test]
    public async Task GliderReplacementWithNoPostConsumptionSlotRejectsAtomically()
    {
        var character = new CharacterMock();
        var bag = CreateBagFor(character, new ItemMock(1, Template(10), 3));
        var glider = BackpackItem(2, 23);
        var equipment = CreateEquipment(character, glider);

        var ok = bag.TryExchangeCraftItems(
            AutoEquipPlan(), 7, equipment, false, [], [], [], out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.BagFull);
        await Assert.That(bag.Items.Single().Count).IsEqualTo(3);
        await Assert.That(equipment.GetItemBySlot((int)EquipmentItemSlot.Backpack))
            .IsSameReferenceAs(glider);
    }

    private static ItemContainer CreateBag(params Item[] items)
    {
        var character = new CharacterMock();
        return CreateBagFor(character, items);
    }

    private static ItemContainer CreateBagFor(CharacterMock character, params Item[] items)
    {
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

    private static EquipmentContainer CreateEquipment(CharacterMock character, params Item[] items)
    {
        // The exchange itself is under test; a null parent avoids unrelated live-stat formula hooks.
        var equipment = new EquipmentContainer(0, SlotType.Equipment, false, null);
        foreach (var item in items)
        {
            item.SlotType = SlotType.Equipment;
            item.Slot = (byte)EquipmentItemSlot.Backpack;
            item.OwnerId = 0;
            item._holdingContainer = equipment;
            equipment.Items.Add(item);
        }
        equipment.UpdateFreeSlotCount();
        return equipment;
    }

    private static CraftTransactionPlan AutoEquipPlan() => new(1,
        [new CraftMaterialRequirement(10, 2, 0)],
        [new CraftProductGrant(22, 1, 0, true)]);

    private static ItemTemplate Template(uint id) =>
        ItemManager.Instance.GetTemplate(id);

    private static Backpack BackpackItem(ulong id, uint templateId) =>
        new(id, Template(templateId), 1);

    private static CharacterMock CreateCharacterWithBag(int materialCount, long money)
    {
        var character = new CharacterMock
        {
            NumInventorySlots = 1,
            Money = money
        };
        var bag = CreateBag(new ItemMock(1, new ItemTemplate
        {
            Id = 10, MaxCount = 10, FixedGrade = 0
        }, materialCount));
        var inventory = (Inventory)RuntimeHelpers.GetUninitializedObject(typeof(Inventory));
        typeof(Inventory).GetProperty(nameof(Inventory.Bag))!
            .SetValue(inventory, bag);
        character.Inventory = inventory;
        return character;
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
