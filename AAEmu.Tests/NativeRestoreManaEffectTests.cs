using AAEmu.Game.Models.Game.Skills.Effects;
using Xunit;

namespace AAEmu.Tests
{
    public class NativeRestoreManaEffectTests
    {
        [Fact]
        public void LevelScaleUsesCasterAndNativeSkillThreshold()
        {
            Assert.Equal(0.125f, RestoreManaEffect.CalculateLevelScale(55, 30, 5), 3);
            Assert.Equal(0f, RestoreManaEffect.CalculateLevelScale(20, 30, 5));
        }

        [Fact]
        public void LevelRangeMatchesNativeAa8Formula()
        {
            var range = RestoreManaEffect.CalculateRestoreRange(
                100f, 55, 30, 5,
                false, 0, 0,
                true, 1.3f, 1, 1,
                false, 10000);

            Assert.Equal(145f, range.Min);
            Assert.Equal(148f, range.Max);
        }

        [Theory]
        [InlineData(150, 10000, 1500)]
        [InlineData(-10, 10000, -100)]
        public void PercentUsesAa8PerMilleScale(int nativeValue, int maxMp, int expected)
        {
            var range = RestoreManaEffect.CalculateRestoreRange(
                0f, 1, 1, 0,
                true, nativeValue, nativeValue,
                false, 0f, 0, 0,
                true, maxMp);

            Assert.Equal(expected, range.Min);
            Assert.Equal(expected, range.Max);
        }

        [Fact]
        public void PeriodicRestoreIsSplitByNativeTickRatio()
        {
            var range = RestoreManaEffect.CalculateRestoreRange(
                0f, 1, 1, 0,
                true, 1000, 1000,
                false, 0f, 0, 0,
                false, 5000, 0.2d);

            Assert.Equal(200f, range.Min);
            Assert.Equal(200f, range.Max);
        }

        [Theory]
        [InlineData(900, 200, 1000, 1000)]
        [InlineData(100, -200, 1000, 0)]
        [InlineData(100, 50, -1, 0)]
        public void ManaDeltaIsClampedToUnitBounds(int current, int delta, int maximum, int expected)
        {
            Assert.Equal(expected, RestoreManaEffect.ClampMana(current, delta, maximum));
        }
    }
}
