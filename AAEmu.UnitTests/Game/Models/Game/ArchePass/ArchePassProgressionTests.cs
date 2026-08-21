using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.ArchePass;

namespace AAEmu.UnitTests.Game.Models.Game.ArchePass;

public class ArchePassProgressionTests
{
    [Test]
    public async Task CurrentTierFollowsRetailPointThresholds()
    {
        var template = CreateTemplate();

        await Assert.That(ArchePassProgression.GetCurrentTier(template, 0)).IsEqualTo(1);
        await Assert.That(ArchePassProgression.GetCurrentTier(template, 9)).IsEqualTo(1);
        await Assert.That(ArchePassProgression.GetCurrentTier(template, 10)).IsEqualTo(2);
        await Assert.That(ArchePassProgression.GetCurrentTier(template, 20)).IsEqualTo(3);
    }

    [Test]
    public async Task PointAdditionSaturatesAtTheLastTier()
    {
        var template = CreateTemplate();

        await Assert.That(ArchePassProgression.AddPoints(template, 19, 100)).IsEqualTo(20L);
        await Assert.That(ArchePassProgression.AddPoints(template, 20, 100)).IsEqualTo(20L);
        await Assert.That(() => ArchePassProgression.AddPoints(template, 0, -1))
            .Throws<ArgumentOutOfRangeException>();
    }

    [Test]
    public async Task ClaimFrontierIsSequentialAndSkipsEmptyRewardRows()
    {
        var template = CreateTemplate();
        var state = CreateState(point: 20, normalTier: 1);

        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true))
            .IsEqualTo(3);

        state.Point = 19;
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true))
            .IsEqualTo(0);
    }

    [Test]
    public async Task NormalAndPremiumCompletionRequireTheirExactRewardFrontiers()
    {
        var template = CreateTemplate();
        var normal = CreateState(point: 20, normalTier: 3);
        await Assert.That(ArchePassProgression.CanCompleteNormal(template, normal)).IsTrue();

        var premium = CreateState(point: 20, normalTier: 3, premiumTier: 1, premium: true);
        await Assert.That(ArchePassProgression.CanCompletePremium(template, premium)).IsFalse();
        premium.LastPremiumRewardTier = 3;
        await Assert.That(ArchePassProgression.CanCompletePremium(template, premium)).IsTrue();
        await Assert.That(ArchePassProgression.CanCompleteNormal(template, premium)).IsFalse();
    }

    [Test]
    public async Task RetailTwoDigitEndYearsAreInterpretedAsTwoThousands()
    {
        await Assert.That(ArchePassGameData.ParseEndAtUtc(26, 8, 20, 12, 30))
            .IsEqualTo(new DateTime(2026, 8, 20, 12, 30, 0, DateTimeKind.Utc));
        await Assert.That(ArchePassGameData.ParseEndAtUtc(0, 0, 0, 0, 0)).IsNull();
    }

    private static ArchePassTemplate CreateTemplate() => new()
    {
        Id = 102,
        CategoryEnabled = true,
        MaxTier = 3,
        Tiers =
        [
            new ArchePassTierTemplate(1, 0, 100, 1, 200, 1),
            new ArchePassTierTemplate(2, 10, 0, 0, 0, 0),
            new ArchePassTierTemplate(3, 20, 300, 1, 400, 1)
        ]
    };

    private static CharacterArchePassState CreateState(
        long point,
        int normalTier,
        int premiumTier = 0,
        bool premium = false) => new()
    {
        Type = 102,
        Point = point,
        Status = ArchePassStatus.Progress,
        Premium = premium,
        LastRewardTier = normalTier,
        LastPremiumRewardTier = premiumTier
    };
}
