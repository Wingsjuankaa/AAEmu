using System;

using AAEmu.Game.Models.Game.Items;

using Xunit;

namespace AAEmu.Tests
{
    public class GradeDistributionSelectorTests
    {
        [Fact]
        public void UnidentifiedHiramInfusionUsesNativeGrandRareArcaneBands()
        {
            var distribution = Distribution(17, 0, 0, 60, 30, 10);

            Assert.Equal(100, GradeDistributionSelector.GetTotalWeight(distribution));
            Assert.Equal((byte)2, GradeDistributionSelector.SelectByRoll(distribution, 0));
            Assert.Equal((byte)2, GradeDistributionSelector.SelectByRoll(distribution, 59));
            Assert.Equal((byte)3, GradeDistributionSelector.SelectByRoll(distribution, 60));
            Assert.Equal((byte)3, GradeDistributionSelector.SelectByRoll(distribution, 89));
            Assert.Equal((byte)4, GradeDistributionSelector.SelectByRoll(distribution, 90));
            Assert.Equal((byte)4, GradeDistributionSelector.SelectByRoll(distribution, 99));
        }

        [Fact]
        public void RadiantHiramInfusionUsesNativeHeroicUniqueCelestialBands()
        {
            var distribution = Distribution(47, 0, 0, 0, 0, 0, 60, 30, 10);

            Assert.Equal((byte)5, GradeDistributionSelector.SelectByRoll(distribution, 0));
            Assert.Equal((byte)6, GradeDistributionSelector.SelectByRoll(distribution, 60));
            Assert.Equal((byte)7, GradeDistributionSelector.SelectByRoll(distribution, 90));
        }

        [Fact]
        public void ZeroWeightGradeCanNeverBeSelectedAtBoundary()
        {
            var distribution = Distribution(23, 0, 0, 0, 60, 30, 10);

            Assert.Equal((byte)3, GradeDistributionSelector.SelectByRoll(distribution, 0));
        }

        [Fact]
        public void InvalidRollIsRejected()
        {
            var distribution = Distribution(17, 0, 0, 60, 30, 10);

            Assert.Throws<ArgumentOutOfRangeException>(
                () => GradeDistributionSelector.SelectByRoll(distribution, 100));
        }

        private static GradeDistributions Distribution(int id, params int[] weights)
        {
            var padded = new int[13];
            weights.CopyTo(padded, 0);
            return new GradeDistributions
            {
                Id = id,
                Weight0 = padded[0],
                Weight1 = padded[1],
                Weight2 = padded[2],
                Weight3 = padded[3],
                Weight4 = padded[4],
                Weight5 = padded[5],
                Weight6 = padded[6],
                Weight7 = padded[7],
                Weight8 = padded[8],
                Weight9 = padded[9],
                Weight10 = padded[10],
                Weight11 = padded[11],
                Weight12 = padded[12]
            };
        }
    }
}
