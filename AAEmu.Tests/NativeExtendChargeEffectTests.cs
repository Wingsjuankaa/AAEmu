using AAEmu.Game.Models.Game.Skills.Effects;
using Xunit;

namespace AAEmu.Tests
{
    public class NativeExtendChargeEffectTests
    {
        [Fact]
        public void Aa8InsulatingLensMatchesVisibleLevelAndMagicAttackFormula()
        {
            var range = ExtendChargeEffect.CalculateChargeRange(
                264f, 50, 10, 0, 1500,
                100000f, 0f, 0f, 0f,
                10000, 10000, 5000, 5000,
                false, 0, 0,
                true, 3f, 1, 1,
                true, 1.5f, 1f,
                false, false, false,
                false, 0, 0, 0);

            // AA8 tooltip at level 50: 792 + 225% Magic Attack.
            Assert.Equal(1009f, range.Min);
            Assert.Equal(1025f, range.Max);
            Assert.Equal(1017f, (range.Min + range.Max) / 2f);
        }

        [Fact]
        public void PercentChargeSelectsMaximumManaOnTheAa10CrosswalkEnum()
        {
            var range = ExtendChargeEffect.CalculateChargeRange(
                0f, 1, 1, 0, 0,
                0f, 0f, 0f, 0f,
                900, 1000, 1200, 2000,
                false, 0, 0,
                false, 0f, 0, 0,
                false, 0f, 0f,
                false, false, false,
                true, 5, 5, 4);

            Assert.Equal((100f, 100f), range);
        }

        [Fact]
        public void ReversedNativeBoundsAreNormalized()
        {
            var range = ExtendChargeEffect.CalculateChargeRange(
                0f, 1, 1, 0, 0,
                0f, 0f, 0f, 0f,
                0, 0, 0, 0,
                true, 900, 100,
                false, 0f, 0, 0,
                false, 0f, 0f,
                false, false, false,
                false, 0, 0, 0);

            Assert.Equal((100f, 900f), range);
        }
    }
}
