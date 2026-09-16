using System.Reflection;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.World.Core.Packets.Wz;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class PlotTimelineLifetimeTests
{
    private sealed class CaptureUnit : Unit
    {
        public List<(string Kind, ushort Tl)> Packets { get; } = [];
        public int Ends { get; private set; }
        public override void OnSkillEnd(Skill skill) => Ends++;
        public override void BroadcastPacket(GamePacket packet, bool self)
        {
            if (packet is SCPlotEventPacket or SCPlotEndedPacket or SCSkillEndedPacket)
                Packets.Add((packet.GetType().Name, BitConverter.ToUInt16(packet.Write(new PacketStream()).GetBytes())));
        }
    }

    private object _previousManager;
    private bool _previousAuthority;
    private Action<ushort, uint> _previousEnd;
    private static readonly FieldInfo Instance = typeof(Singleton<SkillManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;

    [Before(Test)]
    public void Setup()
    {
        _previousManager = Instance.GetValue(null);
        Instance.SetValue(null, new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
        _previousAuthority = WorldIntegration.ZoneAuthority;
        _previousEnd = WorldIntegration.RelayPlotEndedToZone;
        WorldIntegration.ZoneAuthority = true;
    }

    [After(Test)]
    public void Cleanup()
    {
        Instance.SetValue(null, _previousManager);
        WorldIntegration.ZoneAuthority = _previousAuthority;
        WorldIntegration.RelayPlotEndedToZone = _previousEnd;
    }

    private static PlotTree CastingPlot()
    {
        // Same cast-edge structure as r575 43979/4770; shorten only the test's wait.
        var edge = new PlotNextEvent { Casting = true, Delay = 20 };
        var root = new PlotNode { Event = new PlotEventTemplate
            { Id = 42573, SourceUpdateMethodId = 3, TargetUpdateMethodId = 4, Tickets = 1 } };
        root.Event.NextEvents.AddLast(edge);
        root.Children.Add(new PlotNode { ParentNextEvent = edge, Event = new PlotEventTemplate
            { Id = 42574, SourceUpdateMethodId = 3, TargetUpdateMethodId = 4, Tickets = 1 } });
        return new PlotTree(4770) { RootNode = root };
    }

    [Test]
    [Arguments(false)]
    [Arguments(true)]
    public async Task MixedSkill_KeepsTimelineUntilBothConsumersEnd(bool plotFirst)
    {
        var caster = new CaptureUnit { ObjId = 1047 };
        var skill = new Skill(new SkillTemplate { Id = 43979 }) { TlId = SkillTlIdManager.GetNextId(caster) };
        var tl = skill.TlId;
        skill.BeginPlotLifetime(hasNormalExecution: true);
        var callbacks = 0;
        skill.Callback = () => callbacks++;
        var zoneEnds = new List<ushort>();
        WorldIntegration.RelayPlotEndedToZone = (id, _) => zoneEnds.Add(id);
        var state = new PlotState(caster, null, caster, null, null, skill);
        if (!plotFirst)
            skill.EndSkill(caster);
        await CastingPlot().ExecuteAsync(state);
        if (plotFirst)
        {
            await Assert.That(skill.TlId).IsEqualTo(tl);
            await Assert.That(callbacks).IsEqualTo(0);
            skill.EndSkill(caster);
        }
        await Assert.That(zoneEnds.SequenceEqual(new[] { tl })).IsTrue();
        await Assert.That(caster.Packets.All(p => p.Tl == tl)).IsTrue();
        await Assert.That(caster.Packets.Any(p => p.Kind == nameof(SCPlotEventPacket))).IsTrue();
        await Assert.That(callbacks).IsEqualTo(1);
        await Assert.That(caster.Ends).IsEqualTo(1);
        await Assert.That(skill.TlId).IsEqualTo((ushort)0);
    }

    [Test]
    public async Task CancelledMixedCast_ClosesPlotWithOriginalTimeline()
    {
        var caster = new CaptureUnit { ObjId = 1047 };
        var skill = new Skill(new SkillTemplate { Id = 43979 }) { TlId = SkillTlIdManager.GetNextId(caster) };
        var tl = skill.TlId;
        skill.BeginPlotLifetime(hasNormalExecution: true);
        skill.ActivePlotState = new PlotState(caster, null, caster, null, null, skill);
        ushort closedTl = 0;
        WorldIntegration.RelayPlotEndedToZone = (id, _) => closedTl = id;
        skill.Stop(caster);
        await Assert.That(skill.TlId).IsEqualTo(tl);
        await Assert.That(skill.ActivePlotState.CancellationRequested()).IsTrue();
        await CastingPlot().ExecuteAsync(skill.ActivePlotState);
        await Assert.That(closedTl).IsEqualTo(tl);
        await Assert.That(caster.Ends).IsEqualTo(1);
        await Assert.That(skill.TlId).IsEqualTo((ushort)0);
    }

    [Test]
    public async Task PlotOnlyAndOrdinarySkill_KeepSingleCompletion()
    {
        var caster = new CaptureUnit { ObjId = 1047 };
        var ordinary = new Skill(new SkillTemplate { Id = 2 }) { TlId = SkillTlIdManager.GetNextId(caster) };
        ordinary.EndSkill(caster);
        await Assert.That(ordinary.TlId).IsEqualTo((ushort)0);
        var plotOnly = new Skill(new SkillTemplate { Id = 100, PlotOnly = true }) { TlId = SkillTlIdManager.GetNextId(caster) };
        plotOnly.BeginPlotLifetime(hasNormalExecution: false);
        WorldIntegration.RelayPlotEndedToZone = (_, _) => { };
        await CastingPlot().ExecuteAsync(new PlotState(caster, null, caster, null, null, plotOnly));
        await Assert.That(plotOnly.TlId).IsEqualTo((ushort)0);
        await Assert.That(caster.Ends).IsEqualTo(2);
        // The existing native packet carries the complete unsigned 16-bit timeline.
        var frame = new WZPlotEndedPacket(unchecked((short)0xF123)).Encode();
        await Assert.That(Convert.ToHexString(frame)).IsEqualTo("04003B0023F1");
    }
}
