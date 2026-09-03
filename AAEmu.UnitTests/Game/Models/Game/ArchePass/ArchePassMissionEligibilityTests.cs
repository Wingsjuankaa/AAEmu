using AAEmu.Game.Models.Game.ArchePass;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.UnitTests.Game.Models.Game.ArchePass;

public class ArchePassMissionEligibilityTests
{
    private static readonly DateTime Now = new(2026, 9, 3, 20, 0, 0, DateTimeKind.Utc);

    private static ArchePassTemplate Template(DateTime? end = null, bool enabled = true, int id = 18) => new()
    {
        Id = id, CategoryEnabled = enabled, MaxTier = 1, EndAtUtc = end,
        Tiers = [new ArchePassTierTemplate(1, 0, 23633, 1, 23633, 1)]
    };

    private static CharacterArchePassState State() => new()
    {
        Type = 18, Status = ArchePassStatus.Progress, Premium = true,
        Point = 210000, LastRewardTier = 1, LastPremiumRewardTier = 0
    };

    [Test]
    public async Task ActivePremiumAllowsRepeatedChecksWithoutChangingProgressOrClaims()
    {
        var state = State();
        for (var i = 0; i < 3; i++)
            await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, state, Template(), Now)).IsTrue();
        await Assert.That(state.Point).IsEqualTo(210000L);
        await Assert.That(state.LastRewardTier).IsEqualTo(1);
        await Assert.That(state.LastPremiumRewardTier).IsEqualTo(0);
        await Assert.That(state.Premium).IsTrue();
    }

    [Test]
    public async Task NonPremiumOrNonActiveStatesAreRejected()
    {
        var state = State();
        state.Premium = false;
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, state, Template(), Now)).IsFalse();
        state.Premium = true;
        foreach (var status in Enum.GetValues<ArchePassStatus>().Where(s => s != ArchePassStatus.Progress))
        {
            state.Status = status;
            await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, state, Template(), Now)).IsFalse();
        }
    }

    [Test]
    public async Task MissingStorageStateOrCatalogFailClosed()
    {
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(false, State(), Template(), Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, null, Template(), Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), null, Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), new ArchePassTemplate { Id = 18 }, Now)).IsFalse();
        var state = new CharacterArchePassState { Type = 19, Status = ArchePassStatus.Progress, Premium = true };
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, state, Template(), Now)).IsFalse();
    }

    [Test]
    public async Task ExpiryBoundaryAndDisabledCategoryAreRejected()
    {
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), Template(Now.AddSeconds(1)), Now)).IsTrue();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), Template(Now), Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), Template(Now.AddSeconds(-1)), Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, State(), Template(enabled: false), Now)).IsFalse();
    }

    [Test]
    public async Task SwitchingToNormalPassDoesNotInheritPausedPremium()
    {
        var premium = State();
        var normal = new CharacterArchePassState { Type = 19, Status = ArchePassStatus.Owned };
        var states = new Dictionary<int, CharacterArchePassState> { [18] = premium, [19] = normal };
        await Assert.That(ArchePassRegistrationPolicy.TryActivate(states, 19, out _, out _)).IsTrue();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, premium, Template(), Now)).IsFalse();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, normal, Template(id: 19), Now)).IsFalse();
        await Assert.That(ArchePassRegistrationPolicy.TryActivate(states, 18, out _, out _)).IsTrue();
        await Assert.That(ArchePassMissionEligibility.HasPremiumAccess(true, premium, Template(), Now)).IsTrue();
    }

    [Test]
    public async Task PremiumUnitRequirementRejectsMissingPlayerWithoutLoadingStorage()
    {
        var req = new UnitReqs { Id = 68641, OwnerType = "TodayQuestStep", OwnerId = 39,
            KindType = UnitReqsKindType.PremiumArchePass };
        await Assert.That(req.Validate(null, null).ResultKey).IsEqualTo(SkillResultKeys.skill_failure);
    }
}
