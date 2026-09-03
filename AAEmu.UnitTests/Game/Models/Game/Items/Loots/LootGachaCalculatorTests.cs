using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Items.Loots;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Loots;

public class LootGachaCalculatorTests
{
    [Test]
    public async Task Pity_SelectsTheHighestPriorityEligibleAdvancedPack()
    {
        var rows = new[]
        {
            Row(1, add: 0, term: 9, rate: 0, priority: 3),
            Row(2, add: 2, term: 10, rate: 0, priority: 1)
        };

        var selected = LootGachaCalculator.SelectAdvanced(
            rows, 10, new Dictionary<uint, uint>(), new FixedRandom(9_999_999));

        await Assert.That(selected).IsNotNull();
        await Assert.That(selected!.Id).IsEqualTo(2u);
    }

    [Test]
    public async Task AddRound_BlocksChanceUntilCooldownHasElapsed()
    {
        var row = Row(7, add: 5, term: 100, rate: 10_000_000, priority: 1);

        var blocked = LootGachaCalculator.SelectAdvanced([row], 14, new Dictionary<uint, uint> { [7] = 10 }, new FixedRandom(0));
        var eligible = LootGachaCalculator.SelectAdvanced([row], 15, new Dictionary<uint, uint> { [7] = 10 }, new FixedRandom(0));

        await Assert.That(blocked).IsNull();
        await Assert.That(eligible?.Id).IsEqualTo(7u);
    }

    [Test]
    public async Task LastRound_RestartsThePityDistance()
    {
        var row = Row(8, add: 0, term: 10, rate: 0, priority: 1);

        var before = LootGachaCalculator.SelectAdvanced([row], 19, new Dictionary<uint, uint> { [8] = 10 }, new FixedRandom(0));
        var atTerm = LootGachaCalculator.SelectAdvanced([row], 20, new Dictionary<uint, uint> { [8] = 10 }, new FixedRandom(0));

        await Assert.That(before).IsNull();
        await Assert.That(atTerm?.Id).IsEqualTo(8u);
    }

    private static LootGachaAdvancedDefinition Row(
        uint id, uint add, uint term, uint rate, uint priority) => new()
    {
        Id = id,
        GachaLootPackId = 1,
        AddRound = add,
        GiveTerm = term,
        LootPackId = id + 100,
        Rate = rate,
        Priority = priority
    };

    private sealed class FixedRandom(int value) : Random
    {
        public override int Next(int maxValue) => Math.Clamp(value, 0, maxValue - 1);
    }
}
