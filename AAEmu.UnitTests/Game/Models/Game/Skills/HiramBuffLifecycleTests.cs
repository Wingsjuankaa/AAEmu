using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class HiramBuffLifecycleTests
{
    private sealed class QuietUnit : Unit
    {
        public override void BroadcastPacket(GamePacket packet, bool self) { }
    }

    private sealed class Services : IDisposable
    {
        private readonly List<(FieldInfo Field, object Value)> _saved = [];
        public readonly SkillManager Skills = new(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        public readonly Dictionary<uint, BuffTemplate> Templates = [];

        public Services()
        {
            Swap(Skills);
            Swap(new TaskManager(Mock.Of<ITickManager>().Object));
            Swap(new EffectTaskManager(Mock.Of<ITaskManager>().Object));
            var data = new BuffGameData();
            typeof(BuffGameData).GetField("_buffModifiers", BindingFlags.Instance | BindingFlags.NonPublic)!
                .SetValue(data, new Dictionary<uint, List<BuffModifier>>());
            Swap(data);
            typeof(SkillManager).GetField("_buffs", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(Skills, Templates);
        }

        private void Swap<T>(T value) where T : class
        {
            var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
            _saved.Add((field, field.GetValue(null)!));
            field.SetValue(null, value);
        }

        public void Dispose()
        {
            foreach (var (field, value) in _saved)
                field.SetValue(null, value);
        }
    }

    [Test]
    [Arguments(26080u, 26081u)]
    [Arguments(26088u, 26089u)]
    public async Task BrazierStacks_RefreshTwentySeconds_KeepIndex_AndTransformAtFive(uint id, uint destinationId)
    {
        using var services = new Services();
        var source = new BuffTemplate { Id = id, Duration = 20000, MaxStack = 5, StackRule = BuffStackRule.Multiple, TransformBuffId = destinationId };
        var destination = new BuffTemplate { Id = destinationId, Duration = 8000, MaxStack = 10, StackRule = BuffStackRule.Refresh };
        services.Templates[id] = source;
        services.Templates[destinationId] = destination;
        var owner = new QuietUnit { ObjId = 1539 };
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), source, null, DateTime.UtcNow.AddSeconds(-16)) { Passive = true });
        var live = owner.Buffs.GetEffectFromBuffId(id);
        var index = live.Index;
        var oldTask = new DispelTask(live);
        for (var stack = 2; stack <= 4; stack++)
        {
            var before = DateTime.UtcNow;
            owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), source, null, before) { Passive = true });
            await Assert.That(live.Stack).IsEqualTo(stack);
            await Assert.That(live.Index).IsEqualTo(index);
            await Assert.That(live.StartTime >= before).IsTrue();
            await Assert.That(live.EndTime - live.StartTime).IsEqualTo(TimeSpan.FromSeconds(20));
            oldTask.Execute(); // an already dequeued deadline must not expire refreshed stacks
            await Assert.That(live.IsEnded()).IsFalse();
        }
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), source, null, DateTime.UtcNow) { Passive = true });
        await Assert.That(owner.Buffs.GetBuffCountById(id)).IsEqualTo(0);
        await Assert.That(owner.Buffs.GetBuffCountById(destinationId)).IsEqualTo(1);
        await Assert.That(owner.Buffs.GetEffectFromBuffId(destinationId).Duration).IsEqualTo(8000);
    }

    [Test]
    public async Task TimedStackAtCeiling_PreservesCount_WhilePermanentStackNeverSchedulesExpiry()
    {
        using var services = new Services();
        foreach (var duration in new[] { 0, 20000 })
        {
            var source = new BuffTemplate { Id = 26080, Duration = duration, MaxStack = 5, StackRule = BuffStackRule.Multiple };
            services.Templates[source.Id] = source;
            var owner = new QuietUnit { ObjId = 1539 };
            for (var i = 0; i < 6; i++)
                owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), source, null, DateTime.UtcNow) { Passive = true });
            var live = owner.Buffs.GetEffectFromBuffId(source.Id);
            await Assert.That(live.Stack).IsEqualTo(5);
            await Assert.That(live.IsEnded()).IsFalse();
            if (duration == 0)
                await Assert.That(live.EndTime).IsEqualTo(DateTime.MinValue);
        }
    }

    [Test]
    public async Task ZoneAuthoredStack_DoesNotAcquireAWorldRefreshDeadline()
    {
        using var services = new Services();
        var template = new BuffTemplate { Id = 26080, Duration = 20000, MaxStack = 5, StackRule = BuffStackRule.Multiple };
        services.Templates[template.Id] = template;
        var owner = new QuietUnit { ObjId = 1539 };
        var start = DateTime.UtcNow.AddSeconds(-16);
        var live = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), template, null, start) { Passive = true, ZoneAuthored = true };
        owner.Buffs.AddBuff(live);
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), template, null, DateTime.UtcNow) { Passive = true, ZoneAuthored = true });
        await Assert.That(live.StartTime).IsEqualTo(start);
        await Assert.That(live.ZoneAuthored).IsTrue();
    }

    [Test]
    [Arguments(false)]
    [Arguments(true)]
    public async Task BothReadyBraziers_TriggerConvergenceOnce_InEitherOrder(bool reverse)
    {
        using var services = new Services();
        var left = new BuffTemplate { Id = 26081, Duration = 8000, StackRule = BuffStackRule.Refresh };
        var right = new BuffTemplate { Id = 26089, Duration = 8000, StackRule = BuffStackRule.Refresh };
        var complete = new BuffTemplate { Id = 26091, Duration = 3000, StackRule = BuffStackRule.Refresh };
        left.BreakerTags.Add(4616);
        right.BreakerTags.Add(4615);
        foreach (var template in new[] { left, right, complete })
            services.Templates[template.Id] = template;
        typeof(SkillManager).GetField("_taggedBuffs", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(services.Skills, new Dictionary<uint, List<uint>> { [4615] = [26081], [4616] = [26089] });
        typeof(SkillManager).GetField("_buffTriggers", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(services.Skills, new Dictionary<uint, List<BuffTriggerTemplate>>
            {
                [26081] = [new() { Id = 13276, Kind = BuffEventTriggerKind.Breaker, Effect = new BuffEffect { Id = 32565, Buff = complete, Chance = 100, Stack = 1 } }],
                [26089] = [new() { Id = 13277, Kind = BuffEventTriggerKind.Breaker, Effect = new BuffEffect { Id = 32566, Buff = complete, Chance = 100, Stack = 1 } }],
                [26091] = [
                    new() { Id = 13278, Kind = BuffEventTriggerKind.Started, Effect = new DispelEffect { Id = 4710, BuffTagId = 4615, DispelCount = 10, CureCount = 10 } },
                    new() { Id = 13279, Kind = BuffEventTriggerKind.Started, Effect = new DispelEffect { Id = 4711, BuffTagId = 4616, DispelCount = 10, CureCount = 10 } }]
            });
        var owner = new QuietUnit { ObjId = 1539 };
        var first = reverse ? right : left;
        var second = reverse ? left : right;
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), first, null, DateTime.UtcNow) { Passive = true });
        await Assert.That(owner.Buffs.CheckBuff(complete.Id)).IsFalse();
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), second, null, DateTime.UtcNow) { Passive = true });
        await Assert.That(owner.Buffs.GetBuffCountById(complete.Id)).IsEqualTo(1);
        await Assert.That(owner.Buffs.CheckBuff(left.Id)).IsFalse();
        await Assert.That(owner.Buffs.CheckBuff(right.Id)).IsFalse();
        var finished = owner.Buffs.GetEffectFromBuffId(complete.Id);
        var timeouts = 0;
        finished.Events.OnTimeout += (_, _) => timeouts++;
        finished.StartTime = DateTime.UtcNow.AddSeconds(-4);
        new DispelTask(finished).Execute();
        new DispelTask(finished).Execute();
        await Assert.That(timeouts).IsEqualTo(1);
    }

    [Test]
    [Arguments(false)]
    [Arguments(true)]
    public async Task Breaker_DoesNotReactToExpiredPeer_OrMutateZoneOwnedBuff(bool zoneAuthored)
    {
        using var services = new Services();
        var left = new BuffTemplate { Id = 26081, Duration = 8000, StackRule = BuffStackRule.Refresh };
        var right = new BuffTemplate { Id = 26089, Duration = 8000, StackRule = BuffStackRule.Refresh };
        right.BreakerTags.Add(4615);
        services.Templates[left.Id] = left;
        services.Templates[right.Id] = right;
        typeof(SkillManager).GetField("_taggedBuffs", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(services.Skills, new Dictionary<uint, List<uint>> { [4615] = [26081] });
        var owner = new QuietUnit { ObjId = 1539 };
        owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), left, null,
            zoneAuthored ? DateTime.UtcNow : DateTime.UtcNow.AddSeconds(-9)) { Passive = true });
        var incoming = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId), right, null, DateTime.UtcNow)
            { Passive = true, ZoneAuthored = zoneAuthored };
        var triggers = 0;
        incoming.Events.OnBreaker += (_, _) => triggers++;
        owner.Buffs.AddBuff(incoming);
        await Assert.That(triggers).IsEqualTo(0);
        await Assert.That(incoming.IsEnded()).IsFalse();
    }

    [Test]
    public async Task DoodadExpiryAndUpdates_NeverIndexTheZoneUnitTable()
    {
        var oldAuthority = WorldIntegration.ZoneAuthority;
        var oldRemove = WorldIntegration.RelayBuffRemovedToZone;
        var oldUpdate = WorldIntegration.RelayBuffUpdatedToZone;
        var removed = new List<uint>();
        var updated = new List<uint>();
        try
        {
            WorldIntegration.ZoneAuthority = true;
            WorldIntegration.RelayBuffRemovedToZone = (id, _) => removed.Add(id);
            WorldIntegration.RelayBuffUpdatedToZone = (id, _, _, _, _, _) => updated.Add(id);
            foreach (var id in new uint[] { 0, 101000, 101263, 1539, 100999 })
            {
                var owner = new QuietUnit { ObjId = id };
                var template = new BuffTemplate { Id = 23137 };
                var buff = new Buff(owner, owner, new SkillCasterUnit(id), template, null, DateTime.UtcNow) { Index = 2, RelayedToZone = true };
                template.Dispel(owner, owner, buff);
                buff.NotifyUpdated();
            }
            await Assert.That(removed.SequenceEqual(new uint[] { 1539, 100999 })).IsTrue();
            await Assert.That(updated.SequenceEqual(removed)).IsTrue();
        }
        finally
        {
            WorldIntegration.ZoneAuthority = oldAuthority;
            WorldIntegration.RelayBuffRemovedToZone = oldRemove;
            WorldIntegration.RelayBuffUpdatedToZone = oldUpdate;
        }
    }

    [Test]
    public async Task ThreeNativeSymbolStacks_TransformOnce_AndTimeoutFiresOnce()
    {
        using var services = new Services();
        var source = new BuffTemplate { Id = 23652, StackRule = BuffStackRule.Multiple, MaxStack = 3, TransformBuffId = 23653 };
        var destination = new BuffTemplate { Id = 23653, StackRule = BuffStackRule.Refresh, MaxStack = 1, Duration = 1000 };
        services.Templates.Add(source.Id, source);
        services.Templates.Add(destination.Id, destination);
        var owner = new QuietUnit { ObjId = 1539 };
        var sourceBuffs = new List<Buff>();
        for (var i = 0; i < 3; i++)
        {
            var buff = new Buff(owner, owner, new SkillCasterUnit(1539), source, null, DateTime.UtcNow) { Passive = true, AbLevel = 7 };
            sourceBuffs.Add(buff);
            owner.Buffs.AddBuff(buff);
            await Assert.That(owner.Buffs.GetBuffCountById(source.Id)).IsEqualTo(i < 2 ? i + 1 : 0);
            await Assert.That(owner.Buffs.GetBuffCountById(destination.Id)).IsEqualTo(i < 2 ? 0 : 1);
        }
        var transformed = owner.Buffs.GetEffectFromBuffId(destination.Id);
        await Assert.That(transformed.AbLevel).IsEqualTo(7u);
        await Assert.That(transformed.Duration).IsEqualTo(1000);
        var timeouts = 0;
        transformed.Events.OnTimeout += (_, _) => timeouts++;
        transformed.ScheduleEffect(false);
        transformed.ScheduleEffect(false);
        foreach (var old in sourceBuffs)
            old.ScheduleEffect(false); // queued tasks from consumed stacks cannot transform again
        await Assert.That(timeouts).IsEqualTo(1);
        await Assert.That(owner.Buffs.GetBuffCountById(destination.Id)).IsEqualTo(0);
    }

    [Test]
    public async Task MissingDestination_PreservesStacks_AndUnconfiguredBuffsRemainOrdinary()
    {
        using var services = new Services();
        foreach (var transform in new uint[] { 0, 99999 })
        {
            var source = new BuffTemplate { Id = 23652, StackRule = BuffStackRule.Multiple, MaxStack = 3, TransformBuffId = transform };
            services.Templates[source.Id] = source;
            var owner = new QuietUnit { ObjId = 1539 };
            for (var i = 0; i < 3; i++)
                owner.Buffs.AddBuff(new Buff(owner, owner, new SkillCasterUnit(1539), source, null, DateTime.UtcNow) { Passive = true });
            await Assert.That(owner.Buffs.GetBuffCountById(source.Id)).IsEqualTo(3);
        }
    }
}
