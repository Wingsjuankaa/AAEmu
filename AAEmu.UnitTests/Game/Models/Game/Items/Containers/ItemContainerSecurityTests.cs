using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Containers;

public class ItemContainerSecurityTests
{
    [Test]
    public async Task SecuredStack_CannotBePartiallyConsumed()
    {
        var owner = new CharacterMock { Id = 101 };
        var bag = CreateContainer(owner, SlotType.Inventory);
        var item = CreateItem(1, 5);
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Gm, item, 0)).IsTrue();
        item.SetFlag(ItemFlag.Secure);

        var consumed = bag.ConsumeItem(ItemTaskType.SkillReagents, item.TemplateId, 2, null);

        await Assert.That(consumed).IsEqualTo(0);
        await Assert.That(item.Count).IsEqualTo(5);
        await Assert.That(bag.Items.Contains(item)).IsTrue();
    }

    [Test]
    public async Task SecuredItem_CanMoveBetweenContainersOfTheSameOwner()
    {
        var owner = new CharacterMock { Id = 102 };
        var bag = CreateContainer(owner, SlotType.Inventory);
        var bank = CreateContainer(owner, SlotType.Bank);
        var item = CreateItem(2, 1);
        await Assert.That(bag.AddOrMoveExistingItem(ItemTaskType.Gm, item, 0)).IsTrue();
        item.SetFlag(ItemFlag.Secure);

        var moved = bank.AddOrMoveExistingItem(ItemTaskType.SwapItems, item, 0);

        await Assert.That(moved).IsTrue();
        await Assert.That(item._holdingContainer).IsSameReferenceAs(bank);
        await Assert.That(item.OwnerId).IsEqualTo((ulong)owner.Id);
    }

    [Test]
    public async Task SecuredItem_CannotMoveToAnotherOwner()
    {
        var owner = new CharacterMock { Id = 103 };
        var recipient = new CharacterMock { Id = 104 };
        var source = CreateContainer(owner, SlotType.Inventory);
        var target = CreateContainer(recipient, SlotType.Inventory);
        var item = CreateItem(3, 1);
        await Assert.That(source.AddOrMoveExistingItem(ItemTaskType.Gm, item, 0)).IsTrue();
        item.SetFlag(ItemFlag.Secure);

        var moved = target.AddOrMoveExistingItem(ItemTaskType.Invalid, item, 0);

        await Assert.That(moved).IsFalse();
        await Assert.That(item._holdingContainer).IsSameReferenceAs(source);
        await Assert.That(source.Items.Contains(item)).IsTrue();
        await Assert.That(target.Items).IsEmpty();
    }

    private static Item CreateItem(uint id, int count) =>
        new ItemMock(id, new ItemTemplate { Id = 9000 + id, MaxCount = 100 }, count);

    private static ItemContainer CreateContainer(CharacterMock owner, SlotType slotType) =>
        new(owner.Id, slotType, false, owner) { Owner = owner };
}
