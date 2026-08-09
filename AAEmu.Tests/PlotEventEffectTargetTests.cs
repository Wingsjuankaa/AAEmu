using System.Linq;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotEventEffectTargetTests
    {
        [Fact]
        public void LocationTargetExecutesOnceWhenAreaSelectsNoUnits()
        {
            var location = new BaseUnit();
            var targetInfo = new PlotTargetInfo(new BaseUnit(), location);
            var effect = new PlotEventEffect { TargetId = PlotEffectTarget.Location };
            var state = new PlotState(null, null, null, null, null, null);

            var targets = effect.ResolveEffectTargets(state, targetInfo).ToList();

            Assert.Single(targets);
            Assert.Same(location, targets[0]);
        }

        [Fact]
        public void LocationTargetDoesNotRepeatForEachAreaUnit()
        {
            var location = new BaseUnit();
            var targetInfo = new PlotTargetInfo(new BaseUnit(), location);
            targetInfo.EffectedTargets.Add(new BaseUnit());
            targetInfo.EffectedTargets.Add(new BaseUnit());
            var effect = new PlotEventEffect { TargetId = PlotEffectTarget.Location };
            var state = new PlotState(null, null, null, null, null, null);

            var targets = effect.ResolveEffectTargets(state, targetInfo).ToList();

            Assert.Single(targets);
            Assert.Same(location, targets[0]);
        }

        [Fact]
        public void UnitTargetExecutesForEverySelectedAreaUnit()
        {
            var first = new BaseUnit();
            var second = new BaseUnit();
            var targetInfo = new PlotTargetInfo(new BaseUnit(), new BaseUnit());
            targetInfo.EffectedTargets.Add(first);
            targetInfo.EffectedTargets.Add(second);
            var effect = new PlotEventEffect { TargetId = PlotEffectTarget.Target };
            var state = new PlotState(null, null, null, null, null, null);

            var targets = effect.ResolveEffectTargets(state, targetInfo).ToList();

            Assert.Equal(new[] { first, second }, targets);
        }
    }
}
