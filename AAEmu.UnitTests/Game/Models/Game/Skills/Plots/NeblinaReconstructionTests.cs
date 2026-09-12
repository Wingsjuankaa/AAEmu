using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Plots;

[NotInParallel]
public class NeblinaReconstructionTests
{
    private sealed class CaptureUnit : Unit
    {
        public List<byte[]> Events { get; } = [];
        public override void BroadcastPacket(GamePacket packet, bool self)
        {
            if (packet is SCPlotEventPacket plot)
                Events.Add(plot.Write(new PacketStream()).GetBytes());
        }
    }

    private readonly List<(FieldInfo Field, object Owner, object Value)> _saved = [];
    private JsonDocument _fixture;
    private void Replace(FieldInfo field, object owner, object value)
    {
        _saved.Add((field, owner, field.GetValue(owner)));
        field.SetValue(owner, value);
    }

    [Before(Test)]
    public void Setup()
    {
        var assembly = typeof(NeblinaReconstructionTests).Assembly;
        _fixture = JsonDocument.Parse(assembly.GetManifestResourceStream(
            assembly.GetManifestResourceNames().Single(n => n.EndsWith("Neblina2957.json")))!);
        var manager = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        Replace(typeof(Singleton<SkillManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!, null, manager);
        var effects = Rows("special_effects").Select(Map<SpecialEffect>).ToDictionary(e => e.Id, e => (EffectTemplate)e);
        Replace(typeof(SkillManager).GetField("_effects", BindingFlags.Instance | BindingFlags.NonPublic)!, manager,
            new Dictionary<string, Dictionary<uint, EffectTemplate>> { ["SpecialEffect"] = effects });
        var models = ModelManager.Instance;
        var field = typeof(ModelManager).GetField("_modelTypes", BindingFlags.Instance | BindingFlags.NonPublic)!;
        Replace(field, models, Activator.CreateInstance(field.FieldType));
        var world = new WorldManager(Mock.Of<ITickManager>().Object, Mock.Of<IWorldIdManager>().Object,
            new Lazy<IZoneManager>(() => Mock.Of<IZoneManager>().Object),
            new Lazy<IIndunManager>(() => Mock.Of<IIndunManager>().Object),
            new Lazy<IFamilyManager>(() => Mock.Of<IFamilyManager>().Object));
        Replace(typeof(Singleton<WorldManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!, null, world);
    }

    [After(Test)]
    public void Cleanup()
    {
        foreach (var saved in _saved.AsEnumerable().Reverse()) saved.Field.SetValue(saved.Owner, saved.Value);
        _saved.Clear();
        _fixture.Dispose();
    }

    private IEnumerable<JsonElement> Rows(string table) => _fixture.RootElement.GetProperty(table).EnumerateArray();
    private static T Map<T>(JsonElement row) where T : new()
    {
        var result = new T();
        foreach (var property in typeof(T).GetProperties().Where(p => p.CanWrite))
        {
            var key = JsonNamingPolicy.SnakeCaseLower.ConvertName(property.Name);
            if (property.Name == "Kind") key = "kind_id";
            if (!row.TryGetProperty(key, out var value) || value.ValueKind == JsonValueKind.Null) continue;
            object parsed = property.PropertyType == typeof(string) ? value.GetString()! :
                property.PropertyType == typeof(bool) ? value.GetString() == "t" :
                property.PropertyType.IsEnum ? Enum.ToObject(property.PropertyType, value.GetInt32()) :
                Convert.ChangeType(value.GetInt32(), property.PropertyType);
            property.SetValue(result, parsed);
        }
        return result;
    }

    private PlotTree BuildFillerTree()
    {
        var events = Rows("plot_events").Select(Map<PlotEventTemplate>).ToDictionary(e => e.Id);
        var conditions = Rows("plot_conditions").Select(Map<PlotCondition>).ToDictionary(e => e.Id);
        foreach (var row in Rows("plot_effects")) events[row.GetProperty("event_id").GetUInt32()].Effects.AddLast(Map<PlotEventEffect>(row));
        foreach (var row in Rows("plot_event_conditions"))
        {
            var condition = Map<PlotEventCondition>(row);
            condition.Condition = conditions[row.GetProperty("condition_id").GetUInt32()];
            events[row.GetProperty("event_id").GetUInt32()].Conditions.AddLast(condition);
        }
        foreach (var row in Rows("plot_next_events"))
        {
            var edge = Map<PlotNextEvent>(row);
            edge.Event = events[row.GetProperty("next_event_id").GetUInt32()];
            events[row.GetProperty("event_id").GetUInt32()].NextEvents.AddLast(edge);
        }
        var tree = new PlotTree(2957) { RootNode = new PlotNode { Event = events[24570] } };
        // Use the production graph builder, with the native filler entry as the bounded fixture root.
        typeof(PlotBuilder).GetMethod("BuildChildren", BindingFlags.Static | BindingFlags.NonPublic)!
            .Invoke(null, [tree.RootNode, new Dictionary<uint, PlotNode>()]);
        return tree;
    }

    [Test]
    public async Task NativePositionalChain_PointsForward_WithoutTheSpuriousEightMetreLift()
    {
        var events = Rows("plot_events").Select(Map<PlotEventTemplate>).ToDictionary(e => e.Id);
        var owner = new CaptureUnit { ObjId = 100 };
        owner.Transform.Local.Position = new(100, 100, 100);
        var skill = new Skill(new SkillTemplate { Id = 36473 });
        var state = new PlotState(owner, null, owner, null, null, skill);
        skill.ActivePlotState = state;
        foreach (var yaw in new[] { 0f, MathF.PI / 2f, MathF.PI, -MathF.PI / 2f })
        {
            owner.Transform.Local.SetZRotation(yaw);
            for (var sample = 0; sample < 20; sample++)
            {
                var info = new PlotTargetInfo(owner, owner);
                foreach (var id in new uint[] { 24565, 24854, 24575 })
                {
                    info = info.Fork(info.Source, info.Target);
                    info.UpdateTargetInfo(events[id], state);
                    // Native Area.p5=1000 belongs only to the final event.
                    await Assert.That(info.Target.Transform.World.Position.Z).IsEqualTo(id == 24575 ? 101f : 100f);
                }
                var offset = info.Target.Transform.World.Position - owner.Transform.World.Position;
                var forward = new System.Numerics.Vector3(-MathF.Sin(yaw), MathF.Cos(yaw), 0f);
                var projection = System.Numerics.Vector3.Dot(offset, forward);
                // Native forward distance20m (legacy epsilon0.01m) and scatter radius6m.
                await Assert.That(projection).IsGreaterThan(13.9f);
                await Assert.That(projection).IsLessThan(26.1f);
            }
        }
    }

    [Test]
    public async Task NativeFillerPath_ProducesPositionEventsWithoutEnemyUnits()
    {
        var owner = new CaptureUnit { ObjId = 100 };
        owner.Transform.Local.Position = new(100, 100, 100);
        var skill = new Skill(new SkillTemplate { Id = 36473 });
        var state = new PlotState(owner, null, owner, null, null, skill);
        skill.ActivePlotState = state;
        await BuildFillerTree().ExecuteAsync(state);
        var projectiles = owner.Events.Where(body => BitConverter.ToUInt32(body, 2) == 24575).ToList();
        Console.WriteLine($"Neblina native filler events={projectiles.Count}; variable={state.Variables[1]}");
        await Assert.That(projectiles.Count).IsGreaterThan(0);
        foreach (var body in projectiles)
        {
            var stream = new PacketStream(body) { Pos = 10 };
            await Assert.That(stream.ReadByte()).IsEqualTo((byte)PlotObjectType.UNIT);
            stream.ReadBc();
            await Assert.That(stream.ReadByte()).IsEqualTo((byte)PlotObjectType.POSITION);
        }
    }

    [Test]
    public async Task Range8619_DoesNotExpandToTheThirtyMetreSelectionCone()
    {
        var owner = new CaptureUnit { ObjId = 100 };
        var target = new BaseUnit { ObjId = 200 };
        var skill = new Skill(new SkillTemplate { Id = 36473 });
        skill.ActivePlotState = new PlotState(owner, null, target, null, null, skill);
        skill.ActivePlotState.AreaSelectionRadius[target.ObjId] = 30;
        var condition = Rows("plot_conditions").Select(Map<PlotCondition>).Single(c => c.Id == 8619);
        foreach (var (distance, expected) in new[] { (7.9f, true), (8f, true), (8.1f, false), (20f, false) })
        {
            target.Transform.Local.Position = new(distance, 0, 0);
            await Assert.That(condition.Check(owner, null, target, null, null, skill)).IsEqualTo(expected);
        }
    }

    [Test]
    public async Task FixedEffect_RunsOnce_WithManyOrZeroHits()
    {
        var owner = new CaptureUnit { ObjId = 100 };
        var skill = new Skill(new SkillTemplate { Id = 36473 });
        var state = new PlotState(owner, null, owner, null, null, skill);
        skill.ActivePlotState = state;
        var info = new PlotTargetInfo(owner, owner) { EffectedTargets = [new Unit { ObjId = 201 }, new Unit { ObjId = 202 }] };
        var effect = Rows("plot_effects").Where(r => r.GetProperty("actual_id").GetUInt32() == 36838).Select(Map<PlotEventEffect>).Single();
        byte flag = 2;
        effect.ApplyEffect(state, info, new PlotEventTemplate { Id = 24854 }, ref flag);
        await Assert.That(state.Variables[1]).IsEqualTo(1);
        info.EffectedTargets.Clear();
        effect.ApplyEffect(state, info, new PlotEventTemplate { Id = 24854 }, ref flag);
        await Assert.That(state.Variables[1]).IsEqualTo(2);
    }

    [Test]
    public async Task NativeNestedTicketBudgets_AreAvailableForEverySalvo()
    {
        var events = Rows("plot_events").Select(Map<PlotEventTemplate>).ToDictionary(e => e.Id);
        var owner = new CaptureUnit { ObjId = 100 };
        var salvo = new PlotTargetInfo(owner, owner);
        var accepted = 0;
        for (var shot = 0; shot < 11; shot++)
        {
            if (PlotTicketGate.IsExhausted(salvo.Visit(24562), events[24562].Tickets, selfLoop: true)) break;
            var filler = salvo.Fork(owner, owner);
            for (var arrow = 0; arrow < 7; arrow++)
            {
                if (PlotTicketGate.IsExhausted(filler.Visit(24565), events[24565].Tickets)) break;
                accepted++;
                filler = filler.Fork(owner, owner);
            }
            salvo = salvo.Fork(owner, owner);
        }
        // This verifies ticket availability, not the separate variable condition or client rendering.
        await Assert.That(accepted).IsEqualTo(60);
    }

    [Test]
    public async Task SiblingBranchesAndTargets_DoNotConsumeEachOthersTickets()
    {
        var owner = new CaptureUnit { ObjId = 100 };
        var parent = new PlotTargetInfo(owner, owner);
        parent.Visit(1);
        var first = parent.Fork(owner, new Unit { ObjId = 201 });
        var second = parent.Fork(owner, new Unit { ObjId = 202 });
        first.Visit(2); first.Visit(2);
        await Assert.That(second.Visit(2)).IsEqualTo(1);
        await Assert.That(first.Fork(owner, owner).Visit(2)).IsEqualTo(3);
        await Assert.That(second.Visit(1)).IsEqualTo(2);
    }

    [Test]
    public async Task Wire_PreservesUnitIds_AndExcludesPositionAnchors()
    {
        var owner = new CaptureUnit { ObjId = 100 };
        var info = new PlotTargetInfo(owner, owner) { EffectedTargets = [new Unit { ObjId = 201 }, new BaseUnit { ObjId = uint.MaxValue }, new Unit { ObjId = 202 }] };
        foreach (var empty in new[] { false, true })
        {
            if (empty) info.EffectedTargets.Clear();
            var caster = new PlotObject(owner);
            var target = new PlotObject(owner.Transform);
            var body = new SCPlotEventPacket(1, 24575, 36473, caster, target, 0, 0, 2,
                targetUnitIds: info.GetTargetUnitIds(), inputDirection: 7).Write(new PacketStream());
            body.Pos = 10 + caster.Write(new PacketStream()).Count + target.Write(new PacketStream()).Count;
            body.ReadUInt64(); body.ReadBc(); body.ReadUInt16(); body.ReadBc(); body.ReadUInt16();
            var count = body.ReadByte();
            await Assert.That(count).IsEqualTo((byte)(empty ? 0 : 2));
            if (!empty)
            {
                await Assert.That(body.ReadBc()).IsEqualTo(201u);
                await Assert.That(body.ReadBc()).IsEqualTo(202u);
            }
            await Assert.That(body.ReadByte()).IsEqualTo((byte)2);
            await Assert.That(body.ReadByte()).IsEqualTo((byte)7);
            await Assert.That(body.Pos).IsEqualTo(body.Count);
        }
    }
}
