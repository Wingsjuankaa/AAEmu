using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotRandomAreaHeightTests
    {
        [Fact]
        public void Aa8WaveParameterSnapsGeneratedImpactToNearbyTerrain()
        {
            var result = PlotTargetInfo.ResolveRandomAreaHeight(100f, 94f, 8000, true);

            Assert.Equal(94f, result);
        }

        [Fact]
        public void TerrainOutsideCorrectionLimitDoesNotPullAirborneImpactToGround()
        {
            var result = PlotTargetInfo.ResolveRandomAreaHeight(100f, 90f, 8000, true);

            Assert.Equal(100f, result);
        }

        [Fact]
        public void DisabledHeightMapsPreservePreviousTargetHeight()
        {
            var result = PlotTargetInfo.ResolveRandomAreaHeight(100f, 94f, 8000, false);

            Assert.Equal(100f, result);
        }

        [Fact]
        public void NegativeNativeValueUsesItsMagnitudeAsCorrectionLimit()
        {
            var result = PlotTargetInfo.ResolveRandomAreaHeight(100f, 94f, -8000, true);

            Assert.Equal(94f, result);
        }

        [Theory]
        [InlineData(4000, 0f, 0f)]
        [InlineData(4000, 0.5f, 2f)]
        [InlineData(4000, 1f, 4f)]
        [InlineData(-4000, 0.5f, 2f)]
        [InlineData(0, 0.5f, 0f)]
        public void RandomAreaDistanceSamplesTheWholeNativeRadius(
            int maximumDistanceMillimeters,
            float normalizedSample,
            float expectedMeters)
        {
            var result = PlotTargetInfo.ResolveRandomAreaDistance(
                maximumDistanceMillimeters,
                normalizedSample);

            Assert.Equal(expectedMeters, result);
        }

        [Theory]
        [InlineData(-1f, 0f)]
        [InlineData(2f, 4f)]
        public void RandomAreaDistanceClampsUnexpectedSamples(
            float normalizedSample,
            float expectedMeters)
        {
            var result = PlotTargetInfo.ResolveRandomAreaDistance(4000, normalizedSample);

            Assert.Equal(expectedMeters, result);
        }
    }
}
