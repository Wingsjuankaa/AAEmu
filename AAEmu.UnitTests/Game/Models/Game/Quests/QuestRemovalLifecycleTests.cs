using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestRemovalLifecycleTests
{
    private sealed class RecordingAct(QuestComponentTemplate component) : QuestActTemplate(component)
    {
        public int Cleanups { get; private set; }
        public int Drops { get; private set; }
        public override void QuestCleanup(Quest quest)
        {
            Cleanups++;
            quest.RequestEvaluation(); // Inventory changes may request another evaluation.
        }
        public override void QuestDropped(Quest quest) => Drops++;
    }

    [Test]
    public async Task Completion_PreservesHiramCarryoverAndNeverRunsAbandonment()
    {
        var (quest, component, recorder, manager) = CreateQuest();
        // Native9212/4244: retain on completion, destroy only on abandonment.
        // Owner has no Inventory: any erroneous destroy callback fails this regression.
        component.ActTemplates.Add(new QuestActObjItemGather(component)
        {
            ItemId = 46452, Count = 1, Cleanup = false, DestroyWhenDrop = true,
            ThisComponentObjectiveIndex = 0
        });
        quest.Status = QuestStatus.Completed;
        quest.Objectives[0] = 1;
        quest.QuestInitialized();

        await Assert.That(quest.FinalizeRemoval(completed: true, update: false)).IsTrue();
        await Assert.That(recorder.Cleanups).IsEqualTo(1);
        await Assert.That(recorder.Drops).IsEqualTo(0);
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Completed);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        manager.EnqueueEvaluation(Any<Quest>()).WasCalled(Times.Never);
    }

    [Test]
    public async Task Abandonment_StillRunsBothCleanupAndDropCallbacks()
    {
        var (quest, _, recorder, _) = CreateQuest();
        quest.Status = QuestStatus.Progress;
        quest.Objectives[0] = 1;
        await Assert.That(quest.FinalizeRemoval(completed: false, update: false)).IsTrue();
        await Assert.That(recorder.Cleanups).IsEqualTo(1);
        await Assert.That(recorder.Drops).IsEqualTo(1);
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Dropped);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
    }

    [Test]
    public async Task RemovedQuest_IgnoresRepeatedRemovalAndQueuedEvaluation()
    {
        var (quest, _, recorder, manager) = CreateQuest();
        quest.Status = QuestStatus.Completed;
        quest.QuestInitialized();
        await Assert.That(quest.FinalizeRemoval(completed: true, update: false)).IsTrue();
        await Assert.That(quest.FinalizeRemoval(completed: false, update: true)).IsFalse();
        quest.StartingEvaluation();
        quest.RequestEvaluation();
        await Assert.That(quest.RunCurrentStep()).IsFalse();
        await Assert.That(recorder.Cleanups).IsEqualTo(1);
        await Assert.That(recorder.Drops).IsEqualTo(0);
        manager.EnqueueEvaluation(Any<Quest>()).WasCalled(Times.Never);
    }

    private static (Quest Quest, QuestComponentTemplate Component, RecordingAct Recorder, Mock<IQuestManager> Manager) CreateQuest()
    {
        var owner = Mock.Of<ICharacter>();
        var manager = Mock.Of<IQuestManager>();
        var template = new QuestTemplate { Id = 9212 };
        var quest = new Quest(template, owner.Object, manager.Object, Mock.Of<ITaskManager>().Object,
            Mock.Of<ISkillManager>().Object, Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var component = new QuestComponentTemplate(template) { Id = 40046, KindId = QuestComponentKind.Progress };
        var recorder = new RecordingAct(component);
        component.ActTemplates.Add(recorder);
        template.Components.Add(component.Id, component);
        return (quest, component, recorder, manager);
    }
}
