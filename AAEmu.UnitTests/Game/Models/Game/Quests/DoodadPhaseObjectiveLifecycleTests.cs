using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class DoodadPhaseObjectiveLifecycleTests
{
    private object _previousDoodads;
    private object _previousQuests;
    private static FieldInfo SingletonField<T>() where T : class =>
        typeof(Singleton<T>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;

    [Before(Test)]
    public void Setup()
    {
        _previousDoodads = SingletonField<DoodadManager>().GetValue(null);
        _previousQuests = SingletonField<QuestManager>().GetValue(null);
        var doodads = new DoodadManager(null, null, null, null, null, null);
        typeof(DoodadManager).GetField("_funcsByGroups", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(doodads, new Dictionary<uint, List<DoodadFunc>>());
        typeof(DoodadManager).GetField("_phaseFuncs", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(doodads, new Dictionary<uint, List<DoodadPhaseFunc>>());
        SingletonField<DoodadManager>().SetValue(null, doodads);
        SingletonField<QuestManager>().SetValue(null,
            new QuestManager(Mock.Of<ITaskManager>().Object, Mock.Of<IZoneManager>().Object));
    }

    [After(Test)]
    public void Cleanup()
    {
        SingletonField<DoodadManager>().SetValue(null, _previousDoodads);
        SingletonField<QuestManager>().SetValue(null, _previousQuests);
    }

    private sealed class LocalDoodad : Doodad
    {
        public override void BroadcastPacket(GamePacket packet, bool self) { }
    }

    [Test]
    public async Task OminousCave_ServerPhaseChangeCreditsObjectiveOnce()
    {
        var (character, quest, _, _, manager) = CreateObjective();
        var portal = new LocalDoodad { TemplateId = 13378 };
        portal.DoChangePhase(character, 38577);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
        portal.DoChangePhase(character, 38621);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        quest.StartingEvaluation();
        portal.DoChangePhase(character, 38621);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        manager.EnqueueEvaluation(quest).WasCalled(Times.Once);
    }

    [Test]
    public async Task UnrelatedDoodadInvalidPhaseAndOtherCharacterDoNotCredit()
    {
        var (character, quest, _, _, manager) = CreateObjective();
        new LocalDoodad { TemplateId = 13319 }.DoChangePhase(character, 38621);
        var portal = new LocalDoodad { TemplateId = 13378 };
        portal.DoChangePhase(character, 0);
        portal.DoChangePhase(character, -1);
        portal.DoChangePhase(character, 38577);
        portal.DoChangePhase(new Character(new UnitCustomModelParams()) { Id = 99 }, 38621);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
        manager.EnqueueEvaluation(Any<Quest>()).WasCalled(Times.Never);
    }

    [Test]
    public async Task AlternatePhaseIsSupportedAndFinalizedObjectiveStopsListening()
    {
        var (character, quest, template, act, _) = CreateObjective();
        template.Phase2 = 999;
        var portal = new LocalDoodad { TemplateId = 13378 };
        portal.DoChangePhase(character, 999);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        template.FinalizeAction(quest, act);
        quest.Objectives[0] = 0;
        portal.DoChangePhase(character, 38621);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
    }

    private static (Character, Quest, QuestActObjDoodadPhaseCheck, QuestAct, Mock<IQuestManager>) CreateObjective()
    {
        var character = new Character(new UnitCustomModelParams()) { Id = 1007, Name = "Dannia" };
        var manager = Mock.Of<IQuestManager>();
        var template = new QuestTemplate { Id = 9178 };
        var quest = new Quest(template, character, manager.Object, Mock.Of<ITaskManager>().Object,
            Mock.Of<ISkillManager>().Object, Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var componentTemplate = new QuestComponentTemplate(template) { Id = 40049, KindId = QuestComponentKind.Progress };
        var component = new QuestComponent(new QuestStep(QuestComponentKind.Progress, quest), componentTemplate);
        var objective = new QuestActObjDoodadPhaseCheck(componentTemplate)
        {
            ActId = 62346, DetailId = 20, DoodadId = 13378, Phase1 = 38621,
            Phase2 = 0, ThisComponentObjectiveIndex = 0
        };
        var act = new QuestAct(component, objective);
        objective.InitializeAction(quest, act);
        quest.QuestInitialized();
        return (character, quest, objective, act, manager);
    }
}
