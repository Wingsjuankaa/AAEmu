using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class ProjectilePlotLifecycleTests
{
    private sealed class QuietUnit : Unit
    {
        public override void BroadcastPacket(GamePacket packet, bool self) { }
    }
    private object _previous;
    private static readonly FieldInfo Instance = typeof(Singleton<SkillManager>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    [Before(Test)]
    public void Setup()
    {
        _previous = Instance.GetValue(null);
        Instance.SetValue(null, new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
    }
    [After(Test)]
    public void Cleanup() => Instance.SetValue(null, _previous);

    [Test]
    public async Task FiredArrow_WaitsForImpact_WithoutBeingCancelledByNextShot()
    {
        var owner = new QuietUnit { ObjId = 100 };
        var arrow = new Skill(new SkillTemplate { Id = 14835 });
        var state = Plot.BindState(owner, null, owner, null, null, arrow);
        // r575 plot5733 edge71617: a 50 m/s flight, casting=false/channeling=false.
        var edge = new PlotNextEvent { Speed = 50 };
        var node = new PlotNode { Event = new PlotEventTemplate { Id = 61611 } };
        node.Event.NextEvents.AddLast(edge);
        node.Children.Add(new PlotNode { ParentNextEvent = edge });
        node.Execute(state, new PlotTargetInfo(owner, owner));
        await Assert.That(state.IsChanneling).IsFalse();
        Plot.BindState(owner, null, owner, null, null, new Skill(new SkillTemplate { Id = 14836 }));
        await Assert.That(state.CancellationRequested()).IsFalse();
        await Assert.That(ReferenceEquals(arrow.ActivePlotState, state)).IsTrue();
    }

    [Test]
    public async Task RealChannel_SurvivesSiblingEvents_EndsAtChannelEdge_AndCanBeInterrupted()
    {
        var owner = new QuietUnit { ObjId = 100 };
        var skill = new Skill(new SkillTemplate { Id = 200 });
        var state = Plot.BindState(owner, null, owner, null, null, skill);
        var edge = new PlotNextEvent { Channeling = true, Delay = 1000 };
        var start = new PlotNode { Event = new PlotEventTemplate { Id = 1 } };
        start.Event.NextEvents.AddLast(edge);
        start.Children.Add(new PlotNode { ParentNextEvent = edge });
        start.Execute(state, new PlotTargetInfo(owner, owner));
        await Assert.That(state.IsChanneling).IsTrue();
        var sibling = new PlotNode { Event = new PlotEventTemplate { Id = 2 } };
        sibling.Execute(state, new PlotTargetInfo(owner, owner));
        await Assert.That(state.IsChanneling).IsTrue();
        Plot.BindState(owner, null, owner, null, null, new Skill(new SkillTemplate { Id = 201 }));
        await Assert.That(state.CancellationRequested()).IsTrue();
        var end = new PlotNode { Event = new PlotEventTemplate { Id = 3 }, ParentNextEvent = edge };
        end.Execute(state, new PlotTargetInfo(owner, owner));
        await Assert.That(state.IsChanneling).IsFalse();
    }

    [Test]
    public async Task ZoneBuffs_ArrivingDuringLoad_KeepOrder_AndResetDropsOldSession()
    {
        var pending = new PendingZoneBuffs();
        var observed = new List<string>();
        pending.Receive(() => observed.Add("create"));
        pending.Receive(() => observed.Add("remove"));
        await Assert.That(observed.Count).IsEqualTo(0);
        pending.CompleteLoading();
        await Assert.That(string.Join(",", observed)).IsEqualTo("create,remove");
        pending.CompleteLoading();
        await Assert.That(observed.Count).IsEqualTo(2);
        pending.Receive(() => observed.Add("live"));
        await Assert.That(observed.Count).IsEqualTo(3);
        pending.Reset();
        pending.Receive(() => observed.Add("stale"));
        pending.Reset();
        pending.Receive(() => observed.Add("new"));
        pending.CompleteLoading();
        await Assert.That(string.Join(",", observed)).IsEqualTo("create,remove,live,new");
    }
}
