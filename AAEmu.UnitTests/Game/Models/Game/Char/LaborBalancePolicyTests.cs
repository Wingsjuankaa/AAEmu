using AAEmu.Game.Models.Game.Char;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class LaborBalancePolicyTests
{
    [Test]
    public async Task LegacyNegativeAccountLabor_IsNormalizedToZero()
    {
        await Assert.That(LaborBalancePolicy.NormalizeAccount(-23_630)).IsEqualTo(0);
        await Assert.That(LaborBalancePolicy.Available(-3_630, 124)).IsEqualTo(124);
    }

    [Test]
    public async Task Available_WithLargeLocalPool_SaturatesWithoutOverflow()
    {
        await Assert.That(LaborBalancePolicy.Available(short.MaxValue, int.MaxValue)).IsEqualTo(int.MaxValue);
    }

    [Test]
    public async Task Spend_UsesAccountPoolThenLocalPool_ExactlyOnce()
    {
        var planned = LaborBalancePolicy.TryPlanSpend(
            accountLabor: 6,
            localLabor: 20,
            cost: 10,
            out var accountDelta,
            out var localDelta);

        await Assert.That(planned).IsTrue();
        await Assert.That(accountDelta).IsEqualTo(-6);
        await Assert.That(localDelta).IsEqualTo(-4);
        await Assert.That(-(accountDelta + localDelta)).IsEqualTo(10);
    }

    [Test]
    public async Task Spend_WithInsufficientCombinedBalance_HasNoPartialMutationPlan()
    {
        var planned = LaborBalancePolicy.TryPlanSpend(
            accountLabor: -3_630,
            localLabor: 9,
            cost: 10,
            out var accountDelta,
            out var localDelta);

        await Assert.That(planned).IsFalse();
        await Assert.That(accountDelta).IsEqualTo(0);
        await Assert.That(localDelta).IsEqualTo(0);
    }
}
