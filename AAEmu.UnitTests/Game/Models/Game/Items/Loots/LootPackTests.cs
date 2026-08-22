using AAEmu.Game.Models.Game.Items.Loots;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Loots;

public class LootPackTests
{
    [Test]
    public async Task MergeQuestItemsForGroup_QuestOnlyGroup_CreatesSelectionBucket()
    {
        var souleye = new Loot
        {
            Id = 92713,
            Group = 1,
            ItemId = 37890,
            LootPackId = 12359,
            DropRate = 1,
            MinAmount = 1,
            MaxAmount = 1
        };
        var questItemsByGroup = new Dictionary<uint, List<Loot>>
        {
            [1] = [souleye]
        };
        var selectedItemsByGroup = new Dictionary<uint, List<Loot>>();

        LootPack.MergeQuestItemsForGroup(1, questItemsByGroup, selectedItemsByGroup);
        LootPack.MergeQuestItemsForGroup(1, questItemsByGroup, selectedItemsByGroup);

        await Assert.That(selectedItemsByGroup.Keys).IsEquivalentTo([1u]);
        await Assert.That(selectedItemsByGroup[1]).IsEquivalentTo([souleye]);
    }
}
