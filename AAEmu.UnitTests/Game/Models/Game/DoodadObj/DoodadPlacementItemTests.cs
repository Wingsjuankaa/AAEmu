using System.Runtime.CompilerServices;
using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

[NotInParallel]
public class DoodadPlacementItemTests
{
    private object _oldItemManager;

    [Before(Test)]
    public void InstallItemManager()
    {
        var singleton = typeof(Singleton<ItemManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
        _oldItemManager = singleton.GetValue(null);
        var manager = new ItemManager(null, Mock.Of<IItemIdManager>().Object, null, null, null, null);
        typeof(ItemManager).GetField("_allItems", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<ulong, Item>());
        typeof(ItemManager).GetField("_removedItems", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new List<ulong>());
        singleton.SetValue(null, manager);
    }

    [After(Test)]
    public void RestoreItemManager() =>
        typeof(Singleton<ItemManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!
            .SetValue(null, _oldItemManager);

    [Test]
    [Arguments(23635u)] // Vita seed -> 4594 (quest 4294)
    [Arguments(23680u)] // Foal variants -> 4725 / 4727 / 4743
    [Arguments(23681u)]
    [Arguments(23682u)]
    public async Task SuccessfulPlacement_ConsumesSelectedSource_ThenNotifiesQuestOnce(uint template)
    {
        var (character, bag) = Setup();
        var source = Item(1, template, 2);
        var other = Item(2, template + 100, 2);
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, source, 0)).IsTrue();
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, other, 1)).IsTrue();
        var events = new List<(uint Template, int Count)>();
        character.Events.OnItemUse += (_, args) => events.Add((args.ItemId, source.Count));

        await Assert.That(DoodadManager.TryConsumePlacementItem(character, source, [template, other.TemplateId])).IsTrue();
        await Assert.That(source.Count).IsEqualTo(1);
        await Assert.That(other.Count).IsEqualTo(2);
        await Assert.That(events.Count).IsEqualTo(1);
        await Assert.That(events[0]).IsEqualTo((template, 1));
    }

    [Test]
    public async Task RejectedSource_NeverConsumesAnAlternativeOrNotifiesQuest()
    {
        var (character, bag) = Setup();
        var source = Item(1, 23635, 2);
        var alternative = Item(2, 23635, 2);
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, source, 0)).IsTrue();
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, alternative, 1)).IsTrue();
        var events = 0;
        character.Events.OnItemUse += (_, _) => events++;
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, source, [23680u])).IsFalse();
        source.SetFlag(ItemFlag.Secure);
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, source, [23635u])).IsFalse();
        var stale = Item(1, 23635, 2);
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, stale, [23635u])).IsFalse();
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, null, [23635u])).IsFalse();
        await Assert.That(source.Count).IsEqualTo(2);
        await Assert.That(alternative.Count).IsEqualTo(2);
        await Assert.That(events).IsEqualTo(0);
    }

    [Test]
    public async Task ExhaustedSource_CannotBeReplayedAgainstAnotherStack()
    {
        var (character, bag) = Setup();
        var source = Item(1, 23635, 1);
        var alternative = Item(2, 23635, 2);
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, source, 0)).IsTrue();
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Invalid, alternative, 1)).IsTrue();
        var events = 0;
        character.Events.OnItemUse += (_, _) => events++;
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, source, [23635u])).IsTrue();
        await Assert.That(DoodadManager.TryConsumePlacementItem(character, source, [23635u])).IsFalse();
        await Assert.That(source.Count).IsEqualTo(0);
        await Assert.That(alternative.Count).IsEqualTo(2);
        await Assert.That(events).IsEqualTo(1);
    }

    private static ItemMock Item(uint id, uint template, int count) =>
        new(id, new ItemTemplate { Id = template, MaxCount = 100 }, count);

    private static (CharacterMock Character, ItemContainer Bag) Setup()
    {
        var character = new CharacterMock();
        var bag = new ItemContainer(0, SlotType.Inventory, false, null) { ContainerSize = 8 };
        var inventory = (Inventory)RuntimeHelpers.GetUninitializedObject(typeof(Inventory));
        typeof(Inventory).GetProperty(nameof(Inventory.Bag))!.SetValue(inventory, bag);
        character.Inventory = inventory;
        return (character, bag);
    }
}
