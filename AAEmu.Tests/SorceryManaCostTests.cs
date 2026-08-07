using AAEmu.Game.Models.Game.Skills;

using Xunit;

namespace AAEmu.Tests
{
    public class SorceryManaCostTests
    {
        [Fact]
        public void FixedManaCost_IsPreservedWithoutLevelMultiplier()
        {
            var result = Skill.CalculateUnmodifiedManaCost(
                abilityLevel: 55,
                effectiveSkillLevel: 1,
                requiredAbilityLevel: 1,
                castingInc: 0,
                fixedManaCost: 21,
                manaLevelMultiplier: 0d);

            Assert.Equal(21d, result, 8);
        }

        [Fact]
        public void PlotValue2_UsesHundredthsOfManaLevelMultiplier()
        {
            var direct = Skill.CalculateUnmodifiedManaCost(55, 55, 25, 0, 0, 3.3d);
            var plot = Skill.CalculateUnmodifiedManaCost(55, 55, 25, 0, 0, 330 / 100d);

            Assert.Equal(direct, plot, 8);
        }

        [Fact]
        public void CastingInc_AppliesNativeEffectiveSkillRankTerm()
        {
            var withoutRankTerm = Skill.CalculateUnmodifiedManaCost(55, 55, 15, 0, 0, 1.7d);
            var withRankTerm = Skill.CalculateUnmodifiedManaCost(55, 55, 15, 14, 0, 1.7d);

            Assert.Equal(withoutRankTerm * 1.56d, withRankTerm, 8);
        }
    }
}
