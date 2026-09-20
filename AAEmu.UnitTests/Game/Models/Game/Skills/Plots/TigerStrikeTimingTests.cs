using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Plots;

[NotInParallel]
public class TigerStrikeTimingTests
{
    private JsonDocument _fixture;
    private readonly Dictionary<uint, PlotNode> _nodes = [];
    private readonly Dictionary<uint, List<(uint Target, PlotNextEvent Edge)>> _edges = [];
    private object _previousSkillManager;
    private object _previousAnimationManager;
    private static FieldInfo SingletonField<T>() where T : class => typeof(Singleton<T>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private IEnumerable<JsonElement> Rows(string name) => _fixture.RootElement.GetProperty(name).EnumerateArray();

    [Before(Test)]
    public void Setup()
    {
        var assembly = typeof(TigerStrikeTimingTests).Assembly;
        _fixture = JsonDocument.Parse(assembly.GetManifestResourceStream(assembly.GetManifestResourceNames()
            .Single(name => name.EndsWith("TigerLightning2922.json")))!);
        var manager = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        var effects = new Dictionary<string, Dictionary<uint, EffectTemplate>>
        {
            ["SkillController"] = [], ["SpecialEffect"] = []
        };
        foreach (var row in Rows("controllers"))
        {
            var template = new SkillControllerTemplate
            {
                Id = row.GetProperty("id").GetUInt32(), KindId = row.GetProperty("kind_id").GetUInt32()
            };
            for (var i = 0; i < 15; i++) template.Value[i] = row.GetProperty($"value{i + 1}").GetInt32();
            effects["SkillController"][template.Id] = template;
        }
        foreach (var row in Rows("special_effects"))
        {
            var template = new SpecialEffect
            {
                Id = row.GetProperty("id").GetUInt32(),
                SpecialEffectTypeId = (SpecialType)row.GetProperty("special_effect_type_id").GetInt32(),
                Value1 = row.GetProperty("value1").GetInt32()
            };
            effects["SpecialEffect"][template.Id] = template;
        }
        typeof(SkillManager).GetField("_effects", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(manager, effects);
        _previousSkillManager = SingletonField<SkillManager>().GetValue(null);
        SingletonField<SkillManager>().SetValue(null, manager);
        _previousAnimationManager = SingletonField<AnimationManager>().GetValue(null);
        // Anim46/all_co_sk_stop has no entry in the effective r575 combat_sync_event_list.g.
        // Its zero marker must not erase the native leap's completion wait.
        SingletonField<AnimationManager>().SetValue(null, new AnimationManager());
        foreach (var row in Rows("events"))
        {
            var id = row.GetProperty("id").GetUInt32();
            _nodes[id] = new PlotNode { Event = new PlotEventTemplate { Id = id } };
            _edges[id] = [];
        }
        foreach (var row in Rows("effects").OrderBy(row => row.GetProperty("position").GetInt32()))
            _nodes[row.GetProperty("event_id").GetUInt32()].Event.Effects.AddLast(new PlotEventEffect
            {
                ActualId = row.GetProperty("actual_id").GetUInt32(),
                ActualType = row.GetProperty("actual_type").GetString()
            });
        foreach (var row in Rows("edges").OrderBy(row => row.GetProperty("position").GetInt32()))
            _edges[row.GetProperty("event_id").GetUInt32()].Add((row.GetProperty("next_event_id").GetUInt32(), new PlotNextEvent
            {
                Id = row.GetProperty("id").GetUInt32(), Delay = row.GetProperty("delay").GetInt32(),
                Speed = row.GetProperty("speed").GetInt32(),
                Casting = row.GetProperty("casting").GetString() == "t",
                AddAnimCsTime = row.GetProperty("add_anim_cs_time").GetString() == "t",
                UseExeTime = row.GetProperty("use_exe_time").GetString() == "t"
            }));
    }

    [After(Test)]
    public void Cleanup()
    {
        SingletonField<SkillManager>().SetValue(null, _previousSkillManager);
        SingletonField<AnimationManager>().SetValue(null, _previousAnimationManager);
        _fixture.Dispose();
        _nodes.Clear();
        _edges.Clear();
    }

    [Test]
    public async Task NativeGraphKeepsFirstImpactAndSpacesTheThreeHitsBy320Milliseconds()
    {
        var owner = new Unit { ObjId = 1 };
        var target = new Unit { ObjId = 2 };
        var state = new PlotState(owner, null, target, null, null, new Skill(new SkillTemplate()));
        var info = new PlotTargetInfo(owner, target);
        var start = DateTime.UnixEpoch;
        var schedule = new PlotSchedule<uint>();
        schedule.Enqueue(24141, start);
        var damageEvents = new List<(uint Event, long Milliseconds)>();
        var launchTimes = new List<long>();
        // Walk the successful native DAG with the production scheduler and edge calculation.
        // Conditions/damage amounts are outside this timing regression; both paths reuse 24146.
        while (schedule.Count > 0)
        {
            var now = schedule.NextDueUtc!.Value;
            schedule.TryDequeueDue(now, out var id);
            var elapsed = (long)(now - start).TotalMilliseconds;
            if (_nodes[id].Event.Effects.Any(effect => effect.ActualType == "DamageEffect"))
                damageEvents.Add((id, elapsed));
            if (id is 24143 or 24145 or 24152) launchTimes.Add(elapsed);
            foreach (var (child, edge) in _edges[id])
                schedule.Enqueue(child, now.AddMilliseconds(edge.GetDelay(state, info, _nodes[id])));
        }
        await Assert.That(string.Join(",", launchTimes)).IsEqualTo("1,421,741");
        await Assert.That(string.Join(",", damageEvents.Select(hit => hit.Event))).IsEqualTo("27709,24146,24146");
        await Assert.That(string.Join(",", damageEvents.Select(hit => hit.Milliseconds))).IsEqualTo("401,721,1041");
        await Assert.That(damageEvents[^1].Milliseconds - damageEvents[0].Milliseconds).IsEqualTo(640L);
    }

    [Test]
    [Arguments(0, 400)]
    [Arguments(400, 400)]
    [Arguments(650, 650)]
    public async Task EdgeAndLeapStartTogetherAndWaitForTheLaterDeadline(int edgeDelay, int expected)
    {
        var owner = new Unit();
        var state = new PlotState(owner, null, owner, null, null, new Skill(new SkillTemplate()));
        var edge = new PlotNextEvent { Delay = edgeDelay };
        await Assert.That(edge.GetDelay(state, new PlotTargetInfo(owner, owner), _nodes[24143])).IsEqualTo(expected);
    }

    [Test]
    public async Task EdgesWithoutAControllerKeepTheirOwnWait()
    {
        var owner = new Unit();
        var state = new PlotState(owner, null, owner, null, null, new Skill(new SkillTemplate()));
        var edge = new PlotNextEvent { Delay = 735 };
        await Assert.That(edge.GetDelay(state, new PlotTargetInfo(owner, owner), _nodes[24141])).IsEqualTo(735);
    }
}
