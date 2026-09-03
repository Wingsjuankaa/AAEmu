using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.ArchePass;

namespace AAEmu.UnitTests.Game.Models.Game.ArchePass;

public class ArchePassProgressionTests
{
    [Test]
    public async Task LatePremiumUpgradeOpensItsFirstRewardWithoutResettingNormalClaims()
    {
        var template = CreateTemplate();
        var state = CreateState(point: 20, normalTier: 3);
        await Assert.That(ArchePassProgression.CanCompleteNormal(template, state)).IsTrue();
        state.Premium = true;
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, true, true)).IsEqualTo(1);
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true)).IsEqualTo(0);
        await Assert.That(ArchePassProgression.CanCompleteNormal(template, state)).IsFalse();
        await Assert.That(ArchePassProgression.CanCompletePremium(template, state)).IsFalse();
        await Assert.That(state.LastRewardTier).IsEqualTo(3);
        await Assert.That(state.LastPremiumRewardTier).IsEqualTo(0);
        await Assert.That(state.Point).IsEqualTo(20L);
        await Assert.That(state.Status).IsEqualTo(ArchePassStatus.Progress);
    }

    [Test]
    public async Task HellwraithKirinAt7000Points_ClaimOneUnlocksTwoWithoutEnablingThree()
    {
        // Exact r575 arche_pass_tiers rows for pass 19 (first three tiers).
        var template = new ArchePassTemplate
        {
            Id = 19,
            Tiers =
            [
                new(1, 0, 23633, 10, 45508, 10),
                new(2, 5745, 46250, 1, 46250, 2),
                new(3, 11490, 49000, 1, 50370, 2)
            ]
        };
        var state = new CharacterArchePassState { Type = 19, Point = 7000, Status = ArchePassStatus.Progress };
        await Assert.That(ArchePassProgression.GetCurrentTier(template, state.Point)).IsEqualTo(2);
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true)).IsEqualTo(1);
        state.LastRewardTier = 1;
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true)).IsEqualTo(2);
        await Assert.That(state.LastPremiumRewardTier).IsEqualTo(0);
        state.LastRewardTier = 2;
        await Assert.That(ArchePassProgression.GetNextClaimableTier(template, state, false, true)).IsEqualTo(0);
        await Assert.That(state.Point).IsEqualTo(7000L);
    }

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
    public async Task PointDeltaUsesAppliedPointsRatherThanTheRequestedAmount()
    {
        var template = CreateTemplate();
        var point = ArchePassProgression.AddPoints(template, 19, int.MaxValue);
        var change = new ArchePassPointChange(102, 19, point,
            ArchePassProgression.GetCurrentTier(template, point));
        await Assert.That(change.AppliedPoints).IsEqualTo(1);
        await Assert.That(change.Point).IsEqualTo(20L);
        await Assert.That(change.Tier).IsEqualTo(3);

        var capped = new ArchePassPointChange(102, point,
            ArchePassProgression.AddPoints(template, point, 1000), 3);
        await Assert.That(capped.AppliedPoints).IsEqualTo(0);
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
    public async Task RetailTwoDigitEndYearsRemainTheNativeInvalidTimestampSentinel()
    {
        await Assert.That(ArchePassGameData.ParseEndAtUtc(23, 3, 30, 5, 0)).IsNull();
        await Assert.That(ArchePassGameData.ParseEndAtUtc(0, 0, 0, 0, 0)).IsNull();
    }

    [Test]
    public async Task RetailFourDigitEndYearsKeepTheirExactUtcExpiry()
    {
        await Assert.That(ArchePassGameData.ParseEndAtUtc(2023, 7, 27, 5, 0))
            .IsEqualTo(new DateTime(2023, 7, 27, 5, 0, 0, DateTimeKind.Utc));
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
