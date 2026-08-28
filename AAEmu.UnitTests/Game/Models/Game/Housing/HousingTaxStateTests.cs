using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingTaxStateTests
{
    private static readonly DateTime Now = new(2026, 8, 28, 12, 0, 0, DateTimeKind.Utc);

    [Test]
    public async Task PaidWeeklyTaxEnablesPrepayWithoutCountingNormalPayment()
    {
        var state = HousingTaxState.Evaluate(Now, Now.AddDays(14).AddSeconds(-1), 7);

        await Assert.That(state.IsAlreadyPaid).IsTrue();
        await Assert.That(state.WeeksWithoutPay).IsEqualTo((sbyte)-1);
        await Assert.That(state.WeeksPrepay).IsEqualTo((byte)0);
        await Assert.That(state.CanPrepay).IsTrue();
    }

    [Test]
    public async Task AdditionalPeriodsAreCountedAndCappedAtNativeMaximum()
    {
        var one = HousingTaxState.Evaluate(Now, Now.AddDays(21).AddSeconds(-1), 7);
        var five = HousingTaxState.Evaluate(Now, Now.AddDays(49).AddSeconds(-1), 7);
        var beyond = HousingTaxState.Evaluate(Now, Now.AddDays(70), 7);

        await Assert.That(one.WeeksPrepay).IsEqualTo((byte)1);
        await Assert.That(one.CanPrepay).IsTrue();
        await Assert.That(five.WeeksPrepay).IsEqualTo(HousingTaxState.MaxPrepaidWeeks);
        await Assert.That(five.CanPrepay).IsFalse();
        await Assert.That(beyond.WeeksPrepay).IsEqualTo(HousingTaxState.MaxPrepaidWeeks);
        await Assert.That(beyond.CanPrepay).IsFalse();
    }

    [Test]
    public async Task DueAndExpiredStatesRemainDistinct()
    {
        var due = HousingTaxState.Evaluate(Now, Now.AddDays(7), 7);
        var expired = HousingTaxState.Evaluate(Now, Now, 7);
        var expiredForTwoMorePeriods = HousingTaxState.Evaluate(Now, Now.AddDays(-14), 7);

        await Assert.That(due.IsAlreadyPaid).IsFalse();
        await Assert.That(due.WeeksWithoutPay).IsEqualTo((sbyte)0);
        await Assert.That(expired.IsAlreadyPaid).IsFalse();
        await Assert.That(expired.WeeksWithoutPay).IsEqualTo((sbyte)1);
        await Assert.That(expiredForTwoMorePeriods.WeeksWithoutPay).IsEqualTo((sbyte)3);
    }
}
