using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class ColdFlameQuestTests
{
    private readonly List<(FieldInfo Field, object Value)> _saved = [];
    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
        _saved.Add((field, field.GetValue(null))); field.SetValue(null, value);
    }
    [Before(Test)]
    public void Setup()
    {
        Swap(new QuestManager(Mock.Of<ITaskManager>().Object, Mock.Of<IZoneManager>().Object));
        Swap(new TeamManager(null, null, null, null));
    }
    [After(Test)]
    public void Cleanup() { foreach (var (field, value) in _saved) field.SetValue(null, value); }

    private sealed class AppliedEffect : EffectTemplate
    {
        public bool Applied;
        public override bool OnActionTime => false;
        public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source, SkillObject skillObject,
            DateTime time, CompressedGamePackets packetBuilder = null) => Applied = true;
    }

    [Test]
    public async Task FinalBuffTriggerCreditsEffectFireWithOuterEffectIdAfterApply()
    {
        var owner = new Character(null) { Id = 1007, ObjId = 1750 };
        var template = new QuestTemplate { Id = 10045 };
        var quest = new Quest(template, owner, Mock.Of<IQuestManager>().Object, Mock.Of<ITaskManager>().Object,
            Mock.Of<ISkillManager>().Object, Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var componentTemplate = new QuestComponentTemplate(template) { Id = 43662, KindId = QuestComponentKind.Progress };
        var component = new QuestComponent(new QuestStep(QuestComponentKind.Progress, quest), componentTemplate);
        var objective = new QuestActObjEffectFire(componentTemplate)
            { ActId = 69442, EffectId = 83348, Count = 1, ThisComponentObjectiveIndex = 0 };
        var act = new QuestAct(component, objective);
        objective.InitializeAction(quest, act);
        quest.QuestInitialized();
        var effect = new AppliedEffect { Id = 32959 }; // detail id must NOT be used for quest matching
        var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), new BuffTemplate { Id = 26313 }, null, DateTime.UtcNow);
        var trigger = new BuffTrigger(buff, new BuffTriggerTemplate
            { Id = 13393, EffectId = 83348, Effect = effect, Kind = BuffEventTriggerKind.Started });
        var events = 0;
        var appliedBeforeEvent = false;
        owner.Events.OnQuestObjective += (_, args) =>
        {
            if (args.Type != QuestObjectiveEventType.EffectFire) return;
            events++; appliedBeforeEvent = effect.Applied;
        };
        trigger.Execute(owner, EventArgs.Empty);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        await Assert.That(events).IsEqualTo(1);
        await Assert.That(appliedBeforeEvent).IsTrue();
    }

    [Test]
    public async Task RejectedTriggerAndMissingOuterIdDoNotNotifyQuests()
    {
        var buffs = Mock.Of<IBuffs>();
        var owner = new Character(null) { Id = 1007, Buffs = buffs.Object };
        var effect = new AppliedEffect();
        var buff = new Buff(owner, owner, new SkillCasterUnit(0), new BuffTemplate { Id = 26313 }, null, DateTime.UtcNow);
        var data = new BuffTriggerTemplate { EffectId = 83348, Effect = effect, OwnerBuffTagId = 123 };
        var events = 0;
        owner.Events.OnQuestObjective += (_, _) => events++;
        buffs.CheckBuffTag(123).Returns(false);
        new BuffTrigger(buff, data).Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Applied).IsFalse();
        await Assert.That(events).IsEqualTo(0);
        data.OwnerBuffTagId = 0; data.EffectId = 0;
        new BuffTrigger(buff, data).Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Applied).IsTrue();
        await Assert.That(events).IsEqualTo(0);
    }

    [Test]
    public async Task FinishedPersonalUseSelectsLitModelWithoutChangingSharedPhase()
    {
        var owner = new Character(null);
        var doodad = new Doodad { ToNextPhase = true,
            Template = new DoodadTemplate { OnceOneMan = true, ClientDoodad = true } };
        var func = new DoodadFunc { FuncType = nameof(DoodadFuncUse), SkillId = 43968, NextPhase = 44293 };
        var use = new DoodadFuncUse();
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(44293u);
        await Assert.That(doodad.FuncGroupId).IsEqualTo(0u);
        owner.SkillCancelled = true;
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(0u);
        owner.SkillCancelled = false; doodad.ToNextPhase = false;
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(0u);
        doodad.ToNextPhase = true; use.SkillId = 1;
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(0u);
        use.SkillId = 0; func.Count = 2;
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(0u);
        func.Count = 0; doodad.Template.ClientDoodad = false;
        await Assert.That(doodad.GetCompletedPersonalUsePhase(owner, func, use, 43968)).IsEqualTo(0u);
    }
}
