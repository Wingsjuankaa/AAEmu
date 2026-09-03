using AAEmu.Game.Core.Managers;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class LootGachaServiceTests
{
    [Test]
    public async Task RetailBatchCount_AllowsTheFullSelectedStack()
    {
        await Assert.That(LootGachaService.IsSupportedBatchCount(1)).IsTrue();
        await Assert.That(LootGachaService.IsSupportedBatchCount(10)).IsTrue();
        await Assert.That(LootGachaService.IsSupportedBatchCount(300)).IsTrue();
        await Assert.That(LootGachaService.IsSupportedBatchCount(int.MaxValue)).IsTrue();
    }

    [Test]
    public async Task RetailBatchCount_RejectsZeroAndValuesOutsideInventoryRepresentation()
    {
        await Assert.That(LootGachaService.IsSupportedBatchCount(0)).IsFalse();
        await Assert.That(LootGachaService.IsSupportedBatchCount((uint)int.MaxValue + 1)).IsFalse();
        await Assert.That(LootGachaService.IsSupportedBatchCount(uint.MaxValue)).IsFalse();
    }

    [Test]
    public async Task RetailBatchAvailability_SumsEveryMatchingBagStack()
    {
        var splitSourceStacks = new[] { 69, 100, 100 };

        await Assert.That(LootGachaService.CanSatisfyBatchFromStacks(269, splitSourceStacks)).IsTrue();
        await Assert.That(LootGachaService.CanSatisfyBatchFromStacks(270, splitSourceStacks)).IsFalse();
        await Assert.That(LootGachaService.CountFullyConsumedStacks(269, splitSourceStacks)).IsEqualTo(3);
        await Assert.That(LootGachaService.CountFullyConsumedStacks(169, splitSourceStacks)).IsEqualTo(2);
    }
}
