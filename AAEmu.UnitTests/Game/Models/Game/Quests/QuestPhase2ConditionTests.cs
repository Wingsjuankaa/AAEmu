using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestPhase2ConditionTests
{
    [Test]
    public async Task AcceptLevelRange_UsesInclusiveAa10Bounds()
    {
        await Assert.That(QuestActConAcceptLevelRange.ContainsLevel(10, 10, 19)).IsTrue();
        await Assert.That(QuestActConAcceptLevelRange.ContainsLevel(19, 10, 19)).IsTrue();
        await Assert.That(QuestActConAcceptLevelRange.ContainsLevel(9, 10, 19)).IsFalse();
        await Assert.That(QuestActConAcceptLevelRange.ContainsLevel(20, 10, 19)).IsFalse();
        await Assert.That(QuestActConAcceptLevelRange.ContainsLevel(10, 19, 10)).IsFalse();
    }

    [Test]
    public async Task AcceptNpcGroup_RequiresNpcProvenanceAndMembership()
    {
        static bool Contains(uint groupId, uint npcId) => groupId == 97 && npcId == 123;

        await Assert.That(QuestActConAcceptNpcGroup.MatchesAcceptor(QuestAcceptorType.Npc, 123, 97, Contains)).IsTrue();
        await Assert.That(QuestActConAcceptNpcGroup.MatchesAcceptor(QuestAcceptorType.Doodad, 123, 97, Contains)).IsFalse();
        await Assert.That(QuestActConAcceptNpcGroup.MatchesAcceptor(QuestAcceptorType.Npc, 124, 97, Contains)).IsFalse();
    }

    [Test]
    public async Task ReportNpcGroup_MatchesOnlyGroupMembers()
    {
        static bool Contains(uint groupId, uint npcId) => groupId == 1053 && npcId == 21286;

        await Assert.That(QuestActConReportNpcGroup.MatchesNpc(1053, 21286, Contains)).IsTrue();
        await Assert.That(QuestActConReportNpcGroup.MatchesNpc(1053, 20876, Contains)).IsFalse();
        await Assert.That(QuestActConReportNpcGroup.MatchesNpc(0, 21286, Contains)).IsFalse();
    }

    [Test]
    public async Task AcceptComponent_ValidatesSelfAndMaterializedCrossReferences()
    {
        await Assert.That(QuestActConAcceptComponent.MatchesContextReference(10303, 10303, false)).IsTrue();
        await Assert.That(QuestActConAcceptComponent.MatchesContextReference(8536, 8516, true)).IsTrue();
        await Assert.That(QuestActConAcceptComponent.MatchesContextReference(8536, 8516, false)).IsFalse();
        await Assert.That(QuestActConAcceptComponent.MatchesContextReference(0, 8516, true)).IsFalse();
    }

    [Test]
    public async Task CheckGuard_RequiresMatchingLivingNpc()
    {
        await Assert.That(QuestActCheckGuard.IsLiveGuard(19129, 19129, false, 1)).IsTrue();
        await Assert.That(QuestActCheckGuard.IsLiveGuard(19129, 19130, false, 1)).IsFalse();
        await Assert.That(QuestActCheckGuard.IsLiveGuard(19129, 19129, true, 1)).IsFalse();
        await Assert.That(QuestActCheckGuard.IsLiveGuard(19129, 19129, false, 0)).IsFalse();
    }

    [Test]
    public async Task AcceptNpcEmotion_RequiresExactEventProvenance()
    {
        await Assert.That(QuestActConAcceptNpcEmotion.MatchesEmotionStart(QuestAcceptorType.Npc, 21286, 124, 21286, 124)).IsTrue();
        await Assert.That(QuestActConAcceptNpcEmotion.MatchesEmotionStart(QuestAcceptorType.Npc, 21286, 0, 21286, 124)).IsFalse();
        await Assert.That(QuestActConAcceptNpcEmotion.MatchesEmotionStart(QuestAcceptorType.Npc, 21286, 125, 21286, 124)).IsFalse();
        await Assert.That(QuestActConAcceptNpcEmotion.MatchesEmotionStart(QuestAcceptorType.Doodad, 21286, 124, 21286, 124)).IsFalse();
    }
}
