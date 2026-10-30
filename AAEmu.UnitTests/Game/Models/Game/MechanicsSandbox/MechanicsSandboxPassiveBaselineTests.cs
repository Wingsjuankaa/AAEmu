using System.Reflection;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.UnitTests.Utils;
using TUnit.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

[NotInParallel]
public class MechanicsSandboxPassiveBaselineTests
{
    private readonly Dictionary<uint, BuffTemplate> _buffs = [];
    private readonly Dictionary<uint, List<BuffTriggerTemplate>> _triggers = [];
    private SingletonScope<SkillManager> _skills;
    private SingletonScope<BuffGameData> _data;
    private SingletonScope<TaskManager> _tasks;
    private SingletonScope<EffectTaskManager> _effects;

    [Before(Test)]
    public void Setup()
    {
        _buffs.Clear(); _triggers.Clear();
        var skills = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        Set(skills, "_buffs", _buffs); Set(skills, "_buffTriggers", _triggers);
        var data = new BuffGameData();
        Set(data, "_buffModifiers", new Dictionary<uint, List<BuffModifier>>());
        Set(data, "_buffTolerances", new Dictionary<uint, BuffTolerance>());
        Set(data, "_buffTolerancesById", new Dictionary<uint, BuffTolerance>());
        var tasks = new TaskManager(Mock.Of<ITickManager>().Object);
        _skills = new(skills); _data = new(data); _tasks = new(tasks);
        _effects = new(new EffectTaskManager(tasks));
    }

    [After(Test)]
    public void Cleanup()
    {
        _effects.Dispose(); _tasks.Dispose(); _data.Dispose(); _skills.Dispose();
    }

    [Test]
    public async Task Swap_DropsAbandonedTreeAndNestedNonPassiveChildren_UsesCurrentBookOnEveryReset()
    {
        var owner = Owner();
        var old = Passive(owner, 1, 101, AbilityType.Fight);
        Child(101, 102); Child(102, 103);
        old.Apply(owner);
        await Assert.That(All(owner).Single(b => b.Template.Id == 103).Passive).IsFalse();
        var baseline = MechanicsSandboxPassiveBaseline.Capture(owner, All(owner));

        // Same book mutation as Skills.Reset(old): Remove the real passive before dropping it.
        old.Remove(owner); owner.Skills.PassiveBuffs.Remove(old.Id);
        owner.Ability1 = AbilityType.Magic;
        var current = Passive(owner, 2, 201, AbilityType.Magic);
        Child(201, 202); Child(202, 203);
        current.Apply(owner);
        Add(owner, Template(301)); // A newly cast timed effect must never become the baseline.

        Reset(owner, baseline);
        await Assert.That(All(owner).Select(b => b.Template.Id).Order().ToArray())
            .IsEquivalentTo(new uint[] { 201, 202, 203 });
        Reset(owner, baseline);
        await Assert.That(All(owner).Count()).IsEqualTo(3);
        // A stale saved passive still in the dictionary cannot resurrect an inactive tree.
        owner.Skills.PassiveBuffs[old.Id] = old;
        Reset(owner, baseline);
        await Assert.That(owner.Buffs.CheckBuff(101)).IsFalse();
        await Assert.That(owner.Buffs.CheckBuff(103)).IsFalse();
    }

    [Test]
    public async Task Restore_PreservesOriginalNonPassiveMetadata_AndNeverSnapshotsNewTransientBuffs()
    {
        var owner = Owner();
        var template = Template(401, duration: 1000);
        owner.BuffModifiersCache.AddModifier(new BuffModifier
        { BuffId = 401, BuffAttribute = BuffAttribute.Duration, UnitModifierType = UnitModifierType.Percent, Value = 50 });
        var original = Add(owner, template, level: 37, charge: 4);
        var baseline = MechanicsSandboxPassiveBaseline.Capture(owner, All(owner));
        var passive = Passive(owner, 1, 501, AbilityType.Fight);
        passive.Apply(owner);
        Add(owner, Template(601));
        Reset(owner, baseline);
        var restored = All(owner).Single(b => b.Template.Id == 401);
        await Assert.That(restored.Duration).IsEqualTo(original.Duration);
        await Assert.That(restored.Duration).IsEqualTo(1500);
        await Assert.That(restored.AbLevel).IsEqualTo(37u);
        await Assert.That(restored.Charge).IsEqualTo(4);
        await Assert.That(restored.Passive).IsFalse();
        await Assert.That(ReferenceEquals(restored.Caster, original.Caster)).IsTrue();
        await Assert.That(owner.Buffs.CheckBuff(601)).IsFalse();
        await Assert.That(owner.Buffs.CheckBuff(501)).IsTrue();
    }

    [Test]
    public async Task GrantedPassiveOutsideLearnedBook_IsRejectedAtCaptureAndBeforeRestoreMutation()
    {
        var owner = Owner();
        var original = Add(owner, Template(911));
        var baseline = MechanicsSandboxPassiveBaseline.Capture(owner, All(owner));
        // CharacterSkills._grantedPassives uses PassiveBuff.Apply, without adding to PassiveBuffs.
        var granted = new PassiveBuff(new PassiveBuffTemplate { Id = 2, BuffId = Template(912).Id });
        granted.Apply(owner);
        await Assert.That(() => MechanicsSandboxPassiveBaseline.Capture(owner, All(owner)))
            .Throws<InvalidOperationException>();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner); scope.BeginReset();
        await Assert.That(() => scope.Mutate(() => baseline.Restore(owner, scope)))
            .Throws<InvalidOperationException>();
        await Assert.That(All(owner).Contains(original)).IsTrue();
        await Assert.That(owner.Buffs.CheckBuff(912)).IsTrue();
    }

    [Test]
    public async Task NonStartedUnknownEffect_IsRejectedBeforeOriginalOrCurrentBuffsAreRemoved()
    {
        var owner = Owner();
        var original = Add(owner, Template(901));
        var baseline = MechanicsSandboxPassiveBaseline.Capture(owner, All(owner));
        var passive = Passive(owner, 1, 902, AbilityType.Fight);
        _triggers[902] = [new BuffTriggerTemplate { Kind = BuffEventTriggerKind.Attack,
            Effect = new HealEffect() }];
        passive.Apply(owner);
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner); scope.BeginReset();
        await Assert.That(() => scope.Mutate(() => baseline.Restore(owner, scope)))
            .Throws<InvalidOperationException>();
        await Assert.That(All(owner).Contains(original)).IsTrue();
        await Assert.That(owner.Buffs.CheckBuff(902)).IsTrue();
    }

    [Test]
    public async Task UnsafeMutationAndNewUnsupportedClosure_AreRefusedBeforeRemovingAnyBuff()
    {
        var owner = Owner();
        Add(owner, Template(701));
        var baseline = MechanicsSandboxPassiveBaseline.Capture(owner, All(owner));
        await Assert.That(() => baseline.Restore(owner, null)).Throws<InvalidOperationException>();
        var passive = Passive(owner, 1, 801, AbilityType.Fight);
        Child(801, 802); Child(802, 801); // Native recursion is unsafe, reject before apply.
        await Assert.That(() => baseline.Validate(owner)).Throws<InvalidOperationException>();
        await Assert.That(owner.Buffs.CheckBuff(701)).IsTrue();
        owner.Skills.PassiveBuffs.Clear();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner); scope.BeginReset();
        var reconnected = Owner();
        await Assert.That(() => scope.Mutate(() => baseline.Restore(reconnected, scope)))
            .Throws<InvalidOperationException>();
        await Assert.That(owner.Buffs.CheckBuff(701)).IsTrue();
    }

    private static Character Owner()
    {
        var owner = new Character(new UnitCustomModelParams()) { ObjId = 18, Level = 55,
            Ability1 = AbilityType.Fight, Ability2 = AbilityType.Will, Ability3 = AbilityType.Love };
        owner.Skills = new CharacterSkills(owner);
        return owner;
    }

    private BuffTemplate Template(uint id, int duration = 0)
    {
        if (_buffs.TryGetValue(id, out var found)) return found;
        return _buffs[id] = new BuffTemplate { Id = id, Kind = BuffKind.Good, Duration = duration, MaxStack = 1 };
    }

    private PassiveBuff Passive(Character owner, uint id, uint buffId, AbilityType tree)
    {
        Template(buffId);
        var passive = new PassiveBuff(new PassiveBuffTemplate { Id = id, BuffId = buffId, AbilityId = tree });
        owner.Skills.PassiveBuffs[id] = passive;
        return passive;
    }

    private void Child(uint source, uint target)
    {
        Template(source);
        _triggers[source] = [new BuffTriggerTemplate { Kind = BuffEventTriggerKind.Started,
            Effect = new BuffEffect { Buff = Template(target), Chance = 100, Stack = 1 } }];
    }

    private static Buff Add(Unit owner, BuffTemplate template, uint level = 1, int charge = 0)
    {
        var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), template, null, DateTime.MinValue)
        { AbLevel = level, Charge = charge };
        owner.Buffs.AddBuff(buff);
        return buff;
    }

    private static Buff[] All(Unit owner)
    {
        List<Buff> good = [], bad = [], hidden = [];
        owner.Buffs.GetAllBuffs(good, bad, hidden, true);
        return good.Concat(bad).Concat(hidden).ToArray();
    }

    private static void Reset(Character owner, MechanicsSandboxPassiveBaseline baseline)
    {
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner); scope.BeginReset();
        scope.Mutate(() => baseline.Restore(owner, scope));
        scope.CompleteReset();
    }

    private static void Set(object target, string name, object value) =>
        target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);
}
