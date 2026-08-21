using AAEmu.Game.Models.Game.Quests.Acts;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestSupplyItemTests
{
    [Test]
    [Arguments(1, 0, 1)]
    [Arguments(1, 1, 0)]
    [Arguments(1, 3, 0)]
    [Arguments(0, 0, 0)]
    public async Task CalculateMissingSupplyCount_NeverMaterializesZeroOrNegativeItems(
        int authoredCount,
        int foundCount,
        int expected)
    {
        var actual = QuestActSupplyItem.CalculateMissingSupplyCount(authoredCount, foundCount);

        await Assert.That(actual).IsEqualTo(expected);
    }
}
