using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestReportPhaseRestoreTests
{
    private static DoodadFuncQuestReact NativeEdge() => new()
    {
        QuestId = 9180, QuestStatus = QuestStatus.Progress, QuestComponentId = 40073, NextPhase = 38961
    };

    [Test]
    public async Task ReadyAndegaRestoresReachedPhaseFromSavedObjectivesWithoutChangingSharedPhase()
    {
        var quest = CreateQuest();
        quest.Status = QuestStatus.Ready;
        quest.Objectives[1] = 1; // Persisted captain arrival in the reported session.
        var edge = NativeEdge();
        var phase = Doodad.ResolveQuestReactPhase(38607,
            p => p == 38607 ? [edge] : [], _ => (true, quest.Status, 0u),
            react => quest.CanRestoreQuestReportPhase(react, 13393));
        await Assert.That(phase).IsEqualTo(38961u);
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Ready);
        await Assert.That(quest.Objectives[1]).IsEqualTo(1);
    }

    [Test]
    public async Task RejectsMissingProgressWrongRecipientAndUnreachedOrUnspecifiedComponent()
    {
        var quest = CreateQuest();
        var edge = NativeEdge();
        quest.Status = QuestStatus.Ready;
        await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13393)).IsFalse();
        quest.Objectives[1] = 1;
        await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13382)).IsFalse();
        foreach (var status in new[] { QuestStatus.Progress, QuestStatus.Completed, QuestStatus.Dropped })
        {
            quest.Status = status;
            await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13393)).IsFalse();
        }
        quest.Status = QuestStatus.Ready;
        edge.QuestComponentId = 0;
        await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13393)).IsFalse();
        edge.QuestComponentId = 99999;
        await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13393)).IsFalse();
        edge.QuestComponentId = 40073;
        edge.QuestId = 9182;
        await Assert.That(quest.CanRestoreQuestReportPhase(edge, 13393)).IsFalse();
    }

    [Test]
    public async Task CurrentReadyEdgeTakesPriorityOverHistoricalProgressEdge()
    {
        var historical = NativeEdge();
        var current = new DoodadFuncQuestReact { QuestId = 9180, QuestStatus = QuestStatus.Ready, NextPhase = 40000 };
        var phase = Doodad.ResolveQuestReactPhase(38607,
            p => p == 38607 ? [historical, current] : [],
            _ => (true, QuestStatus.Ready, 0u), _ => true);
        await Assert.That(phase).IsEqualTo(40000u);
    }

    private static Quest CreateQuest()
    {
        var template = new QuestTemplate { Id = 9180 };
        var quest = new Quest(template, Mock.Of<ICharacter>().Object, Mock.Of<IQuestManager>().Object,
            Mock.Of<ITaskManager>().Object, Mock.Of<ISkillManager>().Object,
            Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var progress = new QuestComponentTemplate(template) { Id = 40073, KindId = QuestComponentKind.Progress };
        progress.ActTemplates.Add(new QuestActObjSphere(progress) { SphereId = 2814, ThisComponentObjectiveIndex = 1 });
        template.Components.Add(progress.Id, progress);
        var ready = new QuestComponentTemplate(template) { Id = 39878, KindId = QuestComponentKind.Ready };
        ready.ActTemplates.Add(new QuestActConReportDoodad(ready) { DoodadId = 13393 });
        template.Components.Add(ready.Id, ready);
        return quest;
    }
}
