using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
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

    [Test]
    [Arguments(15163u, 45362u)]
    [Arguments(15162u, 45364u)]
    [Arguments(15160u, 45366u)]
    [Arguments(15164u, 45368u)]
    [Arguments(15169u, 44814u)]
    public async Task CluePersonalUseCreditsOnlyItsOwnerAndRetainsSharedPhase(uint doodadId, uint phase)
    {
        var (owner, quest, objective, _, manager) = CreateObjective(doodadId, phase, 10060);
        var doodad = new Doodad { TemplateId = doodadId, ToNextPhase = true,
            Template = new DoodadTemplate { ClientDoodad = true, OnceOneMan = true } };
        var func = new DoodadFunc { NextPhase = (int)phase };
        var use = new DoodadFuncUse();
        doodad.CompletePersonalUsePhase(new Character(null), func, use, 44192);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        await Assert.That(objective.RunAct(quest, null, quest.Objectives[0])).IsTrue();
        await Assert.That(doodad.FuncGroupId).IsEqualTo(0u);
        quest.StartingEvaluation();
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        manager.EnqueueEvaluation(quest).WasCalled(Times.Once);
    }

    [Test]
    public async Task UnfinishedCancelledDeferredAndUnrelatedPersonalUsesDoNotCreditClue()
    {
        var (owner, quest, _, _, manager) = CreateObjective(15163, 45362, 10060);
        var doodad = new Doodad { TemplateId = 15163,
            Template = new DoodadTemplate { ClientDoodad = true, OnceOneMan = true } };
        var func = new DoodadFunc { NextPhase = 45362 };
        var use = new DoodadFuncUse();
        doodad.CompletePersonalUsePhase(owner, func, use, 44192); // ToNextPhase false
        doodad.ToNextPhase = true; owner.SkillCancelled = true;
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        owner.SkillCancelled = false; use.SkillId = 123;
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        use.SkillId = 0; func.Count = 2;
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        func.Count = 0; func.NextPhase = 44803;
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        func.NextPhase = 45362; doodad.TemplateId = 15162;
        doodad.CompletePersonalUsePhase(owner, func, use, 44192);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
        manager.EnqueueEvaluation(Any<Quest>()).WasCalled(Times.Never);
    }

    private static (Character, Quest, QuestActObjDoodadPhaseCheck, QuestAct, Mock<IQuestManager>) CreateObjective(
        uint doodadId = 13378, uint phase = 38621, uint questId = 9178)
    {
        var character = new Character(new UnitCustomModelParams()) { Id = 1007, Name = "Dannia" };
        var manager = Mock.Of<IQuestManager>();
        var template = new QuestTemplate { Id = questId };
        var quest = new Quest(template, character, manager.Object, Mock.Of<ITaskManager>().Object,
            Mock.Of<ISkillManager>().Object, Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var componentTemplate = new QuestComponentTemplate(template) { Id = 40049, KindId = QuestComponentKind.Progress };
        var component = new QuestComponent(new QuestStep(QuestComponentKind.Progress, quest), componentTemplate);
        var objective = new QuestActObjDoodadPhaseCheck(componentTemplate)
        {
            ActId = 62346, DetailId = 20, DoodadId = doodadId, Phase1 = phase,
            Phase2 = 0, ThisComponentObjectiveIndex = 0
        };
        var act = new QuestAct(component, objective);
        objective.InitializeAction(quest, act);
        quest.QuestInitialized();
        return (character, quest, objective, act, manager);
    }
}
