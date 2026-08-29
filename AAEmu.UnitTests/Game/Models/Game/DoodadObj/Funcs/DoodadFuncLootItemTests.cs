using AAEmu.Game.Models.Game.DoodadObj.Funcs;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj.Funcs;

public class DoodadFuncLootItemTests
{
    [Test]
    public async Task NativeChancePrecision_HasExactClosedBoundaries()
    {
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(0, 0)).IsFalse();
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(9_999, 9_998)).IsTrue();
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(9_999, 9_999)).IsFalse();
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(10_000, 9_999)).IsTrue();
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(20_000, 9_999)).IsTrue();
        await Assert.That(DoodadFuncLootItem.IsSuccessfulRoll(10_000, 10_000)).IsFalse();
    }

    [Test]
    public async Task NativeLootCount_IncludesConfiguredMaximum()
    {
        var success = DoodadFuncLootItem.TryGetInclusiveCount(
            new MaximumRandom(), 3, 10, out var count);

        await Assert.That(success).IsTrue();
        await Assert.That(count).IsEqualTo(10);
    }

    [Test]
    public async Task FixedNativeLootCount_IsValid()
    {
        var success = DoodadFuncLootItem.TryGetInclusiveCount(
            new Random(575), 3, 3, out var count);

        await Assert.That(success).IsTrue();
        await Assert.That(count).IsEqualTo(3);
    }

    [Test]
    public async Task InvalidNativeLootRange_FailsClosed()
    {
        var success = DoodadFuncLootItem.TryGetInclusiveCount(
            new Random(575), 10, 3, out var count);

        await Assert.That(success).IsFalse();
        await Assert.That(count).IsEqualTo(0);
    }

    private sealed class MaximumRandom : Random
    {
        public override long NextInt64(long minValue, long maxValue) => maxValue - 1;
    }
}
