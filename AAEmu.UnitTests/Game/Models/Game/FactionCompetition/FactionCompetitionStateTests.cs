using AAEmu.Game.Models.Game.FactionCompetition;

namespace AAEmu.UnitTests.Game.Models.Game.FactionCompetition;

public class FactionCompetitionStateTests
{
    private static FactionCompetitionState Create(uint required = 100,
        FactionCompetitionResetKind reset = FactionCompetitionResetKind.All)
    {
        var state = new FactionCompetitionState(new FactionCompetitionTemplate
        {
            Id = 7,
            ZoneGroupId = 17,
            RequiredPoint = required,
            ResetKind = reset
        });
        state.Restore(false, DateTime.MinValue, DateTime.MinValue,
            [new(1, 0), new(2, 0), new(3, 0)]);
        return state;
    }

    [Test]
    public async Task RankingUsesCompetitionRanksAndStableFactionOrder()
    {
        var state = Create();
        state.Start(DateTime.UtcNow, DateTime.UtcNow.AddMinutes(1));
        state.AddPoint(1, 80);
        state.AddPoint(2, 80);
        state.AddPoint(3, 20);

        var ranks = state.GetRanks();
        await Assert.That(ranks[1]).IsEqualTo(1);
        await Assert.That(ranks[2]).IsEqualTo(1);
        await Assert.That(ranks[3]).IsEqualTo(3);
        await Assert.That(state.Snapshot().Select(row => row.FactionId)).
            IsEquivalentTo(new[] { 1, 2, 3 });
    }

    [Test]
    public async Task WinnerRequiresThresholdAndUniqueTopScore()
    {
        var state = Create();
        state.Start(DateTime.UtcNow, DateTime.UtcNow.AddMinutes(1));
        state.AddPoint(1, 100);
        state.AddPoint(2, 100);
        await Assert.That(state.ResolveWinner()).IsEqualTo(0);

        state.AddPoint(1, 1);
        await Assert.That(state.ResolveWinner()).IsEqualTo(1);
    }

    [Test]
    public async Task WinnerOnlyResetPreservesTheLosingScores()
    {
        var state = Create(10, FactionCompetitionResetKind.WinnerOnly);
        state.Start(DateTime.UtcNow, DateTime.UtcNow.AddMinutes(1));
        state.AddPoint(1, 20);
        state.AddPoint(2, 8);
        state.FinishAndReset(state.ResolveWinner());

        await Assert.That(state.Active).IsFalse();
        await Assert.That(state.GetPoint(1)).IsEqualTo(0u);
        await Assert.That(state.GetPoint(2)).IsEqualTo(8u);
    }

    [Test]
    public async Task PointAdditionSaturatesWithoutOverflow()
    {
        var state = Create();
        state.Start(DateTime.UtcNow, DateTime.UtcNow.AddMinutes(1));
        state.AddPoint(1, uint.MaxValue);
        await Assert.That(state.AddPoint(1, 1)).IsEqualTo(uint.MaxValue);
    }
}
