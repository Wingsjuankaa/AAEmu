using System.Reflection;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Core.Packets;
using AAEmu.UnitTests.Utils;
using TUnit.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

[NotInParallel]
public class MechanicsSandboxBuffBaselineTests
{
    private const uint BuffId = 900001;
    private SingletonScope<SkillManager> _skills;
    private SingletonScope<BuffGameData> _data;
    private SingletonScope<TaskManager> _tasks;
    private SingletonScope<EffectTaskManager> _effects;
    private readonly BuffTemplate _template = new() { Id = BuffId, Duration = 1000, MaxStack = 1 };

    [Before(Test)]
    public void Setup()
    {
        var skills = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        Set(skills, "_buffs", new Dictionary<uint, BuffTemplate> { [BuffId] = _template });
        var data = new BuffGameData();
        Set(data, "_buffModifiers", new Dictionary<uint, List<BuffModifier>>());
        Set(data, "_buffTolerances", new Dictionary<uint, BuffTolerance>());
        Set(data, "_buffTolerancesById", new Dictionary<uint, BuffTolerance>());
        var tasks = new TaskManager(Mock.Of<ITickManager>().Object);
        _skills = new(skills);
        _data = new(data);
        _tasks = new(tasks);
        _effects = new(new EffectTaskManager(tasks));
    }

    [After(Test)]
    public void Cleanup()
    {
        _effects.Dispose(); _tasks.Dispose(); _data.Dispose(); _skills.Dispose();
    }

    [Test]
    public async Task Restore_PreservesAbilityLevelAndDoesNotApplyDurationModifiersTwice()
    {
        var owner = new Unit { ObjId = 18 };
        owner.BuffModifiersCache.AddModifier(new BuffModifier
        { BuffId = BuffId, BuffAttribute = BuffAttribute.Duration, UnitModifierType = UnitModifierType.Percent, Value = 50 });
        var original = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), _template, null, DateTime.MinValue)
        { AbLevel = 55, Stack = 1, Passive = true };
        owner.Buffs.AddBuff(original);
        var snapshot = MechanicsSandboxBuffSnapshot.Capture(original);
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner);
        scope.BeginReset();
        Buff restored = null;
        scope.Mutate(() =>
        {
            original.Exit();
            restored = snapshot.Create(owner, _template);
            ((Buffs)owner.Buffs).RestoreMechanicsSnapshot(restored, snapshot.EffectiveDuration);
        });
        scope.CompleteReset();
        await Assert.That(original.Duration).IsEqualTo(1500);
        await Assert.That(restored.Duration).IsEqualTo(1500);
        await Assert.That(restored.AbLevel).IsEqualTo(55u);
        await Assert.That(restored.Passive).IsTrue();
        await Assert.That(restored.ZoneAuthored).IsFalse();
    }

    [Test]
    public async Task ZoneOwnedBaseline_IsNotPromotedToWorldOwnership()
    {
        var owner = new Unit();
        var native = new Buff(owner, owner, null, _template, null, DateTime.UtcNow)
        { ZoneAuthored = true, AbLevel = 55 };
        var snapshot = MechanicsSandboxBuffSnapshot.Capture(native);
        await Assert.That(snapshot.ZoneAuthored).IsTrue();
        await Assert.That(() => snapshot.Create(owner, _template)).Throws<InvalidOperationException>();
    }

    [Test]
    public async Task DirectOldDispelProcIsRetired_WhileNewBaselineStartupRunsOnTheMutationThread()
    {
        var owner = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner);
        var effect = new CountingEffect();
        BuffTrigger Trigger() => new(new Buff(owner, owner, null, _template, null, DateTime.UtcNow),
            new BuffTriggerTemplate { Effect = effect, Kind = BuffEventTriggerKind.Dispelled });
        var old = Trigger();
        scope.BeginReset();
        BuffTrigger fresh = null;
        scope.Mutate(() =>
        {
            old.Execute(owner, EventArgs.Empty);
            fresh = Trigger();
            fresh.Execute(owner, EventArgs.Empty);
        });
        await Assert.That(effect.Calls).IsEqualTo(1);
        // An ordinary caller is not admitted while reset still owns preparation.
        fresh.Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Calls).IsEqualTo(1);
        scope.CompleteReset();
        old.Execute(owner, EventArgs.Empty);
        fresh.Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Calls).IsEqualTo(2);
    }

    private sealed class CountingEffect : EffectTemplate
    {
        public int Calls { get; private set; }
        public override bool OnActionTime => false;
        public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj, EffectSource source, SkillObject skillObject, DateTime time,
            CompressedGamePackets packetBuilder = null) => Calls++;
    }

    [Test]
    public async Task Clear_RecreatesOrdinaryBaselineCallbacksWithoutReactivatingRetiredOnes()
    {
        var owner = new Unit();
        var effect = new CountingEffect();
        var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(owner);
        BuffTrigger Trigger() => new(new Buff(owner, owner, null, _template, null, DateTime.UtcNow),
            new BuffTriggerTemplate { Effect = effect, Kind = BuffEventTriggerKind.Dispelled });
        var retired = Trigger();
        scope.BeginReset();
        BuffTrigger ordinary = null;
        scope.Mutate(() =>
        {
            scope.RemoveActor(owner);
            ordinary = Trigger();
            scope.Dispose();
        });
        retired.Execute(owner, EventArgs.Empty);
        ordinary.Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Calls).IsEqualTo(1);
    }

    private static void Set(object target, string name, object value) =>
        target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);
}
