using AAEmu.Game.Models.Game.Skills.Effects;
using Xunit;

namespace AAEmu.Tests
{
    public class InsulatingLensFormulaTests
    {
        [Fact]
        public void Level50TooltipAverageIs792Plus225PercentMagicAttack()
        {
            var withoutMagicAttack = ExtendChargeEffect.CalculateChargeRange(
                264f, 50, 10, 0, 1500,
                0f, 0f, 0f, 0f,
                0, 0, 0, 0,
                false, 0, 0,
                true, 3f, 1, 1,
                true, 1.5f, 1f,
                false, false, false,
                false, 0, 0, 0);
            var withHundredMagicAttack = ExtendChargeEffect.CalculateChargeRange(
                264f, 50, 10, 0, 1500,
                100000f, 0f, 0f, 0f,
                0, 0, 0, 0,
                false, 0, 0,
                true, 3f, 1, 1,
                true, 1.5f, 1f,
                false, false, false,
                false, 0, 0, 0);

            Assert.Equal(792f,
                (withoutMagicAttack.Min + withoutMagicAttack.Max) / 2f);
            Assert.Equal(225f,
                (withHundredMagicAttack.Min + withHundredMagicAttack.Max) / 2f - 792f);
        }

        [Theory]
        [InlineData(1, 900, 1000, 1200, 2000, 45)]
        [InlineData(2, 900, 1000, 1200, 2000, 50)]
        [InlineData(3, 900, 1000, 1200, 2000, 60)]
        [InlineData(4, 900, 1000, 1200, 2000, 100)]
        public void PercentResourceEnumSelectsTheExpectedPool(
            int resourceType, int hp, int maxHp, int mp, int maxMp, int expected)
        {
            var range = ExtendChargeEffect.CalculateChargeRange(
                0f, 1, 1, 0, 0,
                0f, 0f, 0f, 0f,
                hp, maxHp, mp, maxMp,
                false, 0, 0,
                false, 0f, 0, 0,
                false, 0f, 0f,
                false, false, false,
                true, 5, 5, resourceType);

            Assert.Equal((float)expected, range.Min);
            Assert.Equal((float)expected, range.Max);
        }
    }
}
