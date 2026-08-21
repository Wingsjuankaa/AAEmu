using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Skills.Static;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestPhase5ActContractTests
{
    [Test]
    public async Task EtcItemObtain_OnlyCountsPositiveMatchingAcquisitionsForItsAct()
    {
        await Assert.That(QuestActEtcItemObtain.MatchesAcquisition(10, 10, 100, 100, 2)).IsTrue();
        await Assert.That(QuestActEtcItemObtain.MatchesAcquisition(9, 10, 100, 100, 2)).IsFalse();
        await Assert.That(QuestActEtcItemObtain.MatchesAcquisition(10, 10, 101, 100, 2)).IsFalse();
        await Assert.That(QuestActEtcItemObtain.MatchesAcquisition(10, 10, 100, 100, 0)).IsFalse();
        await Assert.That(QuestActEtcItemObtain.MatchesAcquisition(10, 10, 100, 100, -1)).IsFalse();
    }

    [Test]
    public async Task EtcItemObtain_UsesCountNormallyAndWeightedCountForScoreQuests()
    {
        await Assert.That(QuestActEtcItemObtain.IsCompleted(2, 3, 0)).IsFalse();
        await Assert.That(QuestActEtcItemObtain.IsCompleted(3, 3, 0)).IsTrue();
        await Assert.That(QuestActEtcItemObtain.IsCompleted(2, 5, 10)).IsTrue();
        await Assert.That(QuestActEtcItemObtain.IsCompleted(1, 5, 10)).IsFalse();
    }

    [Test]
    public async Task SupplySkill_OnlyCompletesAfterSuccessfulSkillExecution()
    {
        await Assert.That(QuestActSupplySkill.IsSuccessful(SkillResult.Success)).IsTrue();
        await Assert.That(QuestActSupplySkill.IsSuccessful(SkillResult.Failure)).IsFalse();
        await Assert.That(QuestActSupplySkill.IsSuccessful(SkillResult.NeedLaborPower)).IsFalse();
    }
}
