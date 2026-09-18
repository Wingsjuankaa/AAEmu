using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Plots;

[NotInParallel]
public class BattlerageHammerTests
{
    private sealed class CaptureUnit : Unit
    {
        public int BuffCreatedPackets { get; private set; }
        public override void BroadcastPacket(GamePacket packet, bool self)
        {
            if (packet is SCBuffCreatedPacket) BuffCreatedPackets++;
        }
    }
    private JsonDocument _fixture;
    private readonly List<(FieldInfo Field, object Value)> _saved = [];

    private void ReplaceSingleton<T>(T instance) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
        _saved.Add((field, field.GetValue(null)));
        field.SetValue(null, instance);
    }

    [Before(Test)]
    public void Setup()
    {
        var assembly = typeof(BattlerageHammerTests).Assembly;
        _fixture = JsonDocument.Parse(assembly.GetManifestResourceStream(
            assembly.GetManifestResourceNames().Single(n => n.EndsWith("BattlerageHammer440.json")))!);
        ReplaceSingleton(new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
        ReplaceSingleton(new EffectTaskManager(Mock.Of<ITaskManager>().Object));
        var buffData = new BuffGameData();
        foreach (var field in typeof(BuffGameData).GetFields(BindingFlags.NonPublic | BindingFlags.Instance))
            if (field.FieldType.IsGenericType && field.FieldType.GetGenericTypeDefinition() == typeof(Dictionary<,>))
                field.SetValue(buffData, Activator.CreateInstance(field.FieldType));
        ReplaceSingleton(buffData);
        ReplaceSingleton(new WorldManager(Mock.Of<ITickManager>().Object, Mock.Of<IWorldIdManager>().Object,
            new Lazy<IZoneManager>(() => Mock.Of<IZoneManager>().Object),
            new Lazy<IIndunManager>(() => Mock.Of<IIndunManager>().Object),
            new Lazy<IFamilyManager>(() => Mock.Of<IFamilyManager>().Object)));
    }

    [After(Test)]
    public void Cleanup()
    {
        foreach (var (field, value) in _saved.AsEnumerable().Reverse()) field.SetValue(null, value);
        _saved.Clear();
        _fixture.Dispose();
    }

    private IEnumerable<JsonElement> Rows(string table) => _fixture.RootElement.GetProperty(table).EnumerateArray();

    private static T Map<T>(JsonElement row) where T : new()
    {
        var result = new T();
        foreach (var property in typeof(T).GetProperties().Where(p => p.CanWrite))
        {
            var key = property.Name switch
            {
                "Kind" => "kind_id", "StackRule" => "stack_rule_id",
                _ => JsonNamingPolicy.SnakeCaseLower.ConvertName(property.Name)
            };
            if (!row.TryGetProperty(key, out var value) || value.ValueKind == JsonValueKind.Null) continue;
            object parsed = property.PropertyType == typeof(string) ? value.GetString()! :
                property.PropertyType == typeof(bool) ? (value.ValueKind == JsonValueKind.String ? value.GetString() == "t" : value.GetInt32() != 0) :
                property.PropertyType.IsEnum ? Enum.ToObject(property.PropertyType, value.GetInt32()) :
                Convert.ChangeType(value.GetDouble(), property.PropertyType);
            property.SetValue(result, parsed);
        }
        return result;
    }

    private PlotEventTemplate Event(uint id)
    {
        var template = Map<PlotEventTemplate>(Rows("plot_events").Single(r => r.GetProperty("id").GetUInt32() == id));
        foreach (var row in Rows("plot_event_conditions").Where(r => r.GetProperty("event_id").GetUInt32() == id))
        {
            var condition = Map<PlotEventCondition>(row);
            condition.Condition = Map<PlotCondition>(Rows("plot_conditions").Single(r =>
                r.GetProperty("id").GetUInt32() == row.GetProperty("condition_id").GetUInt32()));
            template.Conditions.AddLast(condition);
        }
        return template;
    }

    private static Region LocalRegion()
    {
        var region = new Region(null, 4, 5, 142);
        typeof(Region).GetField("_neighbors", BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(region, new[] { region });
        return region;
    }

    [Test]
    [Arguments(3f)]
    [Arguments(12f)]
    [Arguments(15f)]
    public async Task NativeLaunchGate_AcceptsAreaPositionAtRangedTarget(float distance)
    {
        var region = LocalRegion();
        var caster = new Unit { ObjId = 100, Region = region, IsVisible = true };
        var target = new Unit { ObjId = 200, Region = region, IsVisible = true };
        caster.Transform.Local.Position = new(100, 100, 10);
        target.Transform.Local.Position = new(100 + distance, 100, 10);
        var skill = new Skill(new SkillTemplate { Id = 18757 });
        var state = new PlotState(caster, null, target, null, null, skill);
        var info = new PlotTargetInfo(state);
        foreach (var id in new uint[] { 3478, 28784, 3480 })
        {
            if (id != 3478) info = info.Fork(info.Source, info.Target);
            var template = Event(id);
            info.UpdateTargetInfo(template, state);
            await Assert.That(new PlotNode { Event = template }.CheckConditions(state, info)).IsTrue();
        }
        await Assert.That(info.Target.ObjId).IsEqualTo(uint.MaxValue);
        await Assert.That(info.Target.IsVisible).IsFalse(); // Position is never a spawned entity.
        await Assert.That(info.GetTargetUnitIds().Length).IsEqualTo(0);
        await Assert.That(info.Target.Transform.World.Position.X).IsEqualTo(100 + distance);
    }

    [Test]
    public async Task PositionVisibility_DoesNotAdmitMissingOrDistantRegions()
    {
        var condition = new PlotCondition { Kind = PlotConditionType.Visible };
        var caster = new Unit { Region = LocalRegion() };
        var position = new BaseUnit { ObjId = uint.MaxValue };
        await Assert.That(condition.Check(caster, null, position, null, null, null)).IsFalse();
        position.Region = new Region(null, 200, 200, 142);
        await Assert.That(condition.Check(caster, null, position, null, null, null)).IsFalse();
        position.Region = caster.Region;
        await Assert.That(condition.Check(caster, null, position, null, null, null)).IsTrue();
        await Assert.That(condition.Check(null, null, position, null, null, null)).IsFalse();
        await Assert.That(condition.Check(caster, null, null, null, null, null)).IsFalse();
        // A real entity in the same region still has to be visible.
        await Assert.That(condition.Check(caster, null, new Unit { Region = caster.Region }, null, null, null)).IsFalse();
        await Assert.That(condition.Check(caster, null, new Unit { Region = caster.Region, IsVisible = true }, null, null, null)).IsTrue();
    }

    [Test]
    public async Task NativeKnockbackConditions_AcceptPositionalSource()
    {
        var caster = new Unit { ObjId = 100 };
        var target = new Unit { ObjId = 200 };
        var anchor = new BaseUnit { ObjId = uint.MaxValue };
        var state = new PlotState(caster, null, target, null, null, new Skill(new SkillTemplate { Id = 18757 }));
        var info = new PlotTargetInfo(anchor, target);
        var template = Event(28786);
        info.UpdateTargetInfo(template, state);
        await Assert.That(new PlotNode { Event = template }.CheckConditions(state, info)).IsTrue();
    }

    [Test]
    [Arguments(PlotEffectSource.OriginalTarget)]
    [Arguments(PlotEffectSource.Source)]
    [Arguments(PlotEffectSource.Target)]
    public async Task SourceSelectors_PreserveBaseUnitPositions(PlotEffectSource selector)
    {
        var caster = new Unit { ObjId = 100 };
        var anchor = new BaseUnit { ObjId = uint.MaxValue };
        var state = new PlotState(caster, null, anchor, null, null, new Skill(new SkillTemplate()));
        var info = new PlotTargetInfo(anchor, anchor) { EffectedTargets = [caster] };
        var condition = new PlotEventCondition
        {
            SourceId = selector, TargetId = PlotEffectTarget.OriginalSource,
            Condition = new PlotCondition { Kind = PlotConditionType.Relation, Param1 = 5 }
        };
        await Assert.That(condition.CheckCondition(state, info)).IsTrue();
    }

    [Test]
    public async Task NativeStunGate_SelectsOriginalTarget_NotSplashVictim()
    {
        var caster = new Unit { ObjId = 100 };
        var primary = new Unit { ObjId = 200 };
        var secondary = new Unit { ObjId = 201 };
        var anchor = new BaseUnit { ObjId = uint.MaxValue };
        var state = new PlotState(caster, null, primary, null, null, new Skill(new SkillTemplate { Id = 18757 }));
        foreach (var victim in new[] { primary, secondary })
        {
            var info = new PlotTargetInfo(anchor, victim);
            var template = Event(25984);
            info.UpdateTargetInfo(template, state);
            await Assert.That(new PlotNode { Event = template }.CheckConditions(state, info)).IsEqualTo(victim == primary);
        }
    }

    [Test]
    public async Task NativeStunEffect_AppliesOnceAt15Metres_AndRejectsMissedHit()
    {
        var manager = SkillManager.Instance;
        var effect = Map<BuffEffect>(Rows("buff_effects").Single());
        effect.Buff = Map<BuffTemplate>(Rows("buffs").Single());
        typeof(SkillManager).GetField("_buffs", BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(manager,
            new Dictionary<uint, BuffTemplate> { [effect.Buff.Id] = effect.Buff });
        typeof(SkillManager).GetField("_effects", BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(manager,
            new Dictionary<string, Dictionary<uint, EffectTemplate>> { ["BuffEffect"] = new() { [effect.Id] = effect } });
        var caster = new CaptureUnit { ObjId = 100 };
        var target = new CaptureUnit { ObjId = 200 };
        var missed = new CaptureUnit { ObjId = 201 };
        target.Transform.Local.Position = new(15, 0, 0);
        missed.Transform.Local.Position = new(15, 0, 0);
        var skill = new Skill(new SkillTemplate { Id = 18757 });
        skill.HitTypes[missed.ObjId] = SkillHitType.MeleeMiss;
        var state = new PlotState(caster, new SkillCasterUnit(caster.ObjId), target,
            new SkillCastUnitTarget(target.ObjId), null, skill);
        var plotEffect = Map<PlotEventEffect>(Rows("plot_effects").Single(r =>
            r.GetProperty("event_id").GetUInt32() == 25984));
        var info = new PlotTargetInfo(new BaseUnit { ObjId = uint.MaxValue }, target)
            { EffectedTargets = [target, missed] };
        await Assert.That(plotEffect.ActualId).IsEqualTo(effect.Id);
        foreach (var victim in info.EffectedTargets)
            effect.Apply(caster, state.CasterCaster, victim, new SkillCastUnitTarget(victim.ObjId),
                new CastPlot(440, skill.TlId, 25984, 18757), new EffectSource(skill), null, DateTime.UtcNow);
        var buff = target.Buffs.GetEffectFromBuffId(22532);
        await Assert.That(buff).IsNotNull();
        await Assert.That(buff.Template.Stun).IsTrue();
        await Assert.That(buff.Duration).IsEqualTo(1500);
        await Assert.That(target.Buffs.GetBuffCountById(22532)).IsEqualTo(1);
        await Assert.That(target.BuffCreatedPackets).IsEqualTo(1);
        await Assert.That(missed.Buffs.GetEffectFromBuffId(22532)).IsNull();
        await Assert.That(missed.BuffCreatedPackets).IsEqualTo(0);
    }
}
