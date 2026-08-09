using AAEmu.Game.Models.Game.Skills;
using Xunit;

namespace AAEmu.Tests
{
    public class ArcherySkillUnitRequirementTests
    {
        [Theory]
        [InlineData(0u, SkillUnitRequirement.BowHoldableId, true)]
        [InlineData(0u, SkillUnitRequirement.ShotgunHoldableId, false)]
        [InlineData(0u, 0u, false)]
        [InlineData(2u, SkillUnitRequirement.ShotgunHoldableId, true)]
        [InlineData(2u, SkillUnitRequirement.BowHoldableId, false)]
        [InlineData(1u, SkillUnitRequirement.BowHoldableId, false)]
        public void EquipRangedDistinguishesAa8BowAndShotgun(
            uint requirementValue,
            uint holdableId,
            bool expected)
        {
            Assert.Equal(
                expected,
                SkillUnitRequirement.MatchesEquipRanged(requirementValue, holdableId));
        }

        [Fact]
        public void NoBuffTagRejectsOnlyWhenForbiddenTagIsPresent()
        {
            Assert.True(SkillUnitRequirement.MatchesNoBuffTag(false));
            Assert.False(SkillUnitRequirement.MatchesNoBuffTag(true));
        }

        [Theory]
        [InlineData(29, 100, 1u, 30u, true)]
        [InlineData(30, 100, 1u, 30u, false)]
        [InlineData(1, 100, 1u, 30u, true)]
        [InlineData(299, 1000, 1u, 30u, true)]
        [InlineData(300, 1000, 1u, 30u, false)]
        [InlineData(29, 100, 0u, 30u, true)]
        public void TargetHealthLessThanUsesExactStrictAa8Boundary(
            int hp,
            int maxHp,
            uint percentageMode,
            uint threshold,
            bool expected)
        {
            Assert.Equal(
                expected,
                SkillUnitRequirement.MatchesTargetHealthLessThan(
                    hp, maxHp, percentageMode, threshold));
        }
    }
}
