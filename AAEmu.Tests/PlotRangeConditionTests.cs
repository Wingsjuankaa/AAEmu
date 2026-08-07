using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotRangeConditionTests
    {
        [Fact]
        public void EdgeDistanceUsesBothRealModelRadii()
        {
            var distance = Unit.CalculateEdgeDistance(42f, 1.5f, 2.5f);

            Assert.Equal(38f, distance);
        }

        [Fact]
        public void EdgeDistanceNeverBecomesNegative()
        {
            var distance = Unit.CalculateEdgeDistance(1f, 2f, 3f);

            Assert.Equal(0f, distance);
        }

        [Theory]
        [InlineData(0f, 0, 35, true)]
        [InlineData(35f, 0, 35, true)]
        [InlineData(35.01f, 0, 35, false)]
        [InlineData(40f, 0, 40, true)]
        public void SorceryRangeConditionsUseInclusiveNativeBounds(
            float edgeDistance,
            int minimum,
            int maximum,
            bool expected)
        {
            Assert.Equal(expected, PlotCondition.MatchesRange(edgeDistance, minimum, maximum));
        }
    }
}
