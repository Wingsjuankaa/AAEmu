using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class BlessUthstinCalculatorTests
{
    [Test]
    public async Task Resolve_RejectsADecreaseThatWouldTakeTheVisibleStatBelowZero()
    {
        var definition = CreateDefinition(10, 10, [1, 0, 0, 0, 0], [0, 0, 0, 1, 0]);

        var rejected = BlessUthstinCalculator.Resolve(
            definition, [0, 0, 0, 0, 0], [10, 10, 10, 9, 10], 200, new Random(1));
        var accepted = BlessUthstinCalculator.Resolve(
            definition, [0, 0, 0, 0, 0], [10, 10, 10, 10, 10], 200, new Random(1));

        await Assert.That(rejected).IsNull();
        await Assert.That(accepted).IsNotNull();
        await Assert.That(accepted.IncreaseStat).IsEqualTo(BlessUthstinStat.Strength);
        await Assert.That(accepted.DecreaseStat).IsEqualTo(BlessUthstinStat.Intelligence);
    }

    [Test]
    public async Task Resolve_AllowsAnEqualExchangeAtThePositiveStatMaximum()
    {
        var definition = CreateDefinition(1, 1, [0, 1, 0, 0, 0], [1, 0, 0, 0, 0]);

        var roll = BlessUthstinCalculator.Resolve(
            definition, [200, 0, 0, 0, 0], [100, 100, 100, 100, 100], 200, new Random(2));

        await Assert.That(roll).IsNotNull();
        await Assert.That(roll.IncreaseStat).IsEqualTo(BlessUthstinStat.Dexterity);
        await Assert.That(roll.DecreaseStat).IsEqualTo(BlessUthstinStat.Strength);
    }

    [Test]
    public async Task BuildCandidates_NeverSelectsTheSameIncreaseAndDecreaseStat()
    {
        var definition = CreateDefinition(1, 1, [1, 1, 1, 1, 1], [1, 1, 1, 1, 1]);

        var candidates = BlessUthstinCalculator.BuildCandidates(
            definition, [0, 0, 0, 0, 0], [10, 10, 10, 10, 10], 200);

        await Assert.That(candidates.Count).IsEqualTo(20);
        await Assert.That(candidates.All(candidate => candidate.Increase != candidate.Decrease)).IsTrue();
    }

    [Test]
    [Arguments(0, 1)]
    [Arguments(1, 2)]
    [Arguments(2, 5)]
    [Arguments(3, 10)]
    public async Task RequiredItemCount_UsesTheNativeSquarePlusOneFormula(int count, int expected)
    {
        await Assert.That(CharacterBlessUthstin.GetRequiredItemCount(count)).IsEqualTo(expected);
    }

    [Test]
    public async Task Confirmation_MustMatchEveryServerPreviewField()
    {
        var preview = new BlessUthstinRoll(
            42822, 1, BlessUthstinStat.Strength, BlessUthstinStat.Intelligence, 1, 1, 0);

        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 0, 3, 1, 1, 0)).IsTrue();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42325, 0, 3, 1, 1, 0)).IsFalse();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 1, 3, 1, 1, 0)).IsFalse();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 0, 4, 1, 1, 0)).IsFalse();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 0, 3, 2, 1, 0)).IsFalse();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 0, 3, 1, 2, 0)).IsFalse();
        await Assert.That(CharacterBlessUthstin.MatchesPending(preview, 42822, 0, 3, 1, 1, 1)).IsFalse();
    }

    private static ItemBlessUthstinDefinition CreateDefinition(
        int rise,
        int drop,
        int[] riseWeights,
        int[] dropWeights) =>
        new()
        {
            ItemId = 42822,
            FunctionId = 1,
            RiseCount = rise,
            DropCount = drop,
            RiseWeights = riseWeights,
            DropWeights = dropWeights
        };
}
