using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestPhase4RewardTests
{
    [Test]
    public async Task CompetitionRank_RoundTripsEveryAcceptedRank()
    {
        for (var rank = 1; rank <= 4; rank++)
        {
            var encoded = QuestActObjFactionCompetition.EncodeRank(4, rank);
            await Assert.That(encoded).IsGreaterThan(0);
            await Assert.That(QuestActObjFactionCompetition.DecodeRank(4, encoded)).IsEqualTo(rank);
        }
    }

    [Test]
    public async Task CompetitionRank_RejectsRanksOutsideAuthoredThreshold()
    {
        await Assert.That(QuestActObjFactionCompetition.EncodeRank(3, 0)).IsEqualTo(0);
        await Assert.That(QuestActObjFactionCompetition.EncodeRank(3, 4)).IsEqualTo(0);
        await Assert.That(QuestActObjFactionCompetition.DecodeRank(3, 4)).IsEqualTo(0);
    }

    [Test]
    public async Task RankedItem_OnlyMatchesItsExactRank()
    {
        await Assert.That(QuestActSupplyRankedItem.ShouldGrant(2, 2)).IsTrue();
        await Assert.That(QuestActSupplyRankedItem.ShouldGrant(2, 1)).IsFalse();
        await Assert.That(QuestActSupplyRankedItem.ShouldGrant(2, 3)).IsFalse();
    }

    [Test]
    public async Task SocialPointDelta_SaturatesAndRejectsNegativeInput()
    {
        await Assert.That(QuestRewardProgressManager.CalculateSaturatedDelta(uint.MaxValue - 3, 10)).IsEqualTo(3u);
        await Assert.That(QuestRewardProgressManager.CalculateSaturatedDelta(100, -1)).IsEqualTo(0u);
        await Assert.That(QuestRewardProgressManager.CalculateSaturatedDelta(100, 25)).IsEqualTo(25u);
        await Assert.That(QuestRewardProgressManager.CalculateSaturatedDelta(ulong.MaxValue - 2, 8)).IsEqualTo(2ul);
    }

    [Test]
    public async Task FamilyProgress_CrossesRetailLevelsAndCapsAtMaximum()
    {
        (uint Level, uint TotalExp)[] levels = [(1, 0), (2, 15_000), (3, 45_000)];

        var first = QuestManager.AdvanceFamilyProgress(1, 14_900, 100, levels);
        await Assert.That(first).IsEqualTo(new QuestManager.FamilyProgress(2, 0, 100));

        var cap = QuestManager.AdvanceFamilyProgress(2, 44_950, 100, levels);
        await Assert.That(cap).IsEqualTo(new QuestManager.FamilyProgress(3, 0, 50));

        var alreadyCapped = QuestManager.AdvanceFamilyProgress(3, 0, 100, levels);
        await Assert.That(alreadyCapped).IsEqualTo(new QuestManager.FamilyProgress(3, 0, 0));
    }

    [Test]
    public async Task FamilyProgress_CanCrossEveryRetailLevelInOneGrant()
    {
        (uint Level, uint TotalExp)[] levels = [(1, 0), (2, 15_000), (3, 45_000)];
        var progress = QuestManager.AdvanceFamilyProgress(1, 0, 60_000, levels);
        await Assert.That(progress).IsEqualTo(new QuestManager.FamilyProgress(3, 0, 60_000));
    }

    [Test]
    public async Task FactionChange_UsesMotherRootForExpeditionCompatibility()
    {
        await Assert.That(QuestRewardProgressManager.ResolveFactionRoot((FactionsEnum)200, FactionsEnum.NuiaAlliance))
            .IsEqualTo(FactionsEnum.NuiaAlliance);
        await Assert.That(QuestRewardProgressManager.ResolveFactionRoot(FactionsEnum.Pirate, (FactionsEnum)114))
            .IsEqualTo((FactionsEnum)114);
        await Assert.That(QuestRewardProgressManager.ShouldLeaveExpedition(FactionsEnum.HaranyaAlliance,
            FactionsEnum.NuiaAlliance)).IsTrue();
        await Assert.That(QuestRewardProgressManager.ShouldLeaveExpedition(FactionsEnum.NuiaAlliance,
            FactionsEnum.NuiaAlliance)).IsFalse();
    }

    [Test]
    public async Task RewardLedger_FailsClosedForPendingConflictAndUnavailableStates()
    {
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Absent, true)).IsTrue();
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Absent, false)).IsFalse();
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Completed, false)).IsTrue();
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Pending, true)).IsFalse();
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Conflict, true)).IsFalse();
        await Assert.That(QuestRewardLedgerManager.CanProceed(QuestRewardLedgerState.Unavailable, true)).IsFalse();
    }

    [Test]
    public async Task Phase4RewardTypes_AreConcreteQuestTemplates()
    {
        var expected = new HashSet<string>
        {
            "QuestActSupplyActability", "QuestActSupplyArchePassPoint", "QuestActSupplyContributionPoint",
            "QuestActSupplyExpeditionExp", "QuestActSupplyFactionChange", "QuestActSupplyFamilyExp",
            "QuestActSupplyLeadershipPoint", "QuestActSupplyLocalLp", "QuestActSupplyRankedItem",
            "QuestActSupplyResidentCharge", "QuestActSupplyResidentPoint", "QuestActSupplyResultRankedItem",
            "QuestActSupplySkill"
        };
        var actual = typeof(QuestActSupplyActability).Assembly.GetTypes()
            .Where(type => !type.IsAbstract && type.IsSubclassOf(typeof(QuestActTemplate)))
            .Select(type => type.Name).ToHashSet();
        await Assert.That(expected.IsSubsetOf(actual)).IsTrue();
    }

    [Test]
    public async Task Phase4RewardTypes_AllUseThePreflightLedgerBase()
    {
        var types = typeof(QuestActSupplyPhase4).Assembly.GetTypes()
            .Where(type => !type.IsAbstract && type.Name.StartsWith("QuestActSupply") &&
                           type.GetInterfaces().Contains(typeof(IQuestRewardPreflight)))
            .ToArray();

        await Assert.That(types.Length).IsEqualTo(13);
        await Assert.That(types.All(type => type.IsSubclassOf(typeof(QuestActSupplyPhase4)))).IsTrue();
    }
}
