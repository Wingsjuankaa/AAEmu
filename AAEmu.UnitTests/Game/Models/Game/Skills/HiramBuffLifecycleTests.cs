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
