using System.Linq;

using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;

using Xunit;

namespace AAEmu.Tests
{
    public class PlotNextEventWeightTests
    {
        [Theory]
        [InlineData(0, 2723u)]
        [InlineData(94, 2723u)]
        [InlineData(95, 41816u)]
        [InlineData(99, 41816u)]
        [InlineData(100, 2723u)]
        public void RainOfFireFinalImpactSelectsExactlyOneNativeWeightedBranch(
            int roll,
            uint expectedEventId)
        {
            var normal = Node(2723, 95);
            var fiveTimesDamage = Node(41816, 5);

            var selected = PlotTree.SelectNextChildrenByWeight(
                new[] {normal, fiveTimesDamage},
                roll);

            Assert.Single(selected);
            Assert.Equal(expectedEventId, selected.Single().Event.Id);
        }

        [Fact]
        public void UnweightedEdgesRemainAlongsideOneWeightedChoice()
        {
            var unconditional = Node(10, 0);
            var first = Node(20, 1);
            var second = Node(30, 3);

            var selected = PlotTree.SelectNextChildrenByWeight(
                new[] {unconditional, first, second},
                3);

            Assert.Equal(new[] {10u, 30u}, selected.Select(node => node.Event.Id));
            Assert.Equal(4, PlotTree.GetTotalNextEventWeight(new[] {unconditional, first, second}));
        }

        private static PlotNode Node(uint eventId, int weight)
        {
            return new PlotNode
            {
                Event = new PlotEventTemplate {Id = eventId},
                ParentNextEvent = new PlotNextEvent {Weight = weight}
            };
        }
    }
}
