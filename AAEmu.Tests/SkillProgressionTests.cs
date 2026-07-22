using AAEmu.Game.Models.Game.Char;
using Xunit;

namespace AAEmu.Tests
{
    public class SkillProgressionTests
    {
        [Theory]
        [InlineData(1, 1, 0, 1)]
        [InlineData(15, 15, 6, 1)]
        [InlineData(21, 15, 6, 2)]
        [InlineData(55, 15, 6, 7)]
        public void TryCalculateSkillLevel_ValidProgression_ReturnsExpectedLevel(
            int abilityLevel, int requiredLevel, int levelStep, byte expectedLevel)
        {
            var result = CharacterSkills.TryCalculateSkillLevel(
                abilityLevel, requiredLevel, levelStep, out var skillLevel);

            Assert.True(result);
            Assert.Equal(expectedLevel, skillLevel);
        }

        [Fact]
        public void TryCalculateSkillLevel_AbilityBelowRequirement_RejectsSkill()
        {
            var result = CharacterSkills.TryCalculateSkillLevel(14, 15, 6, out var skillLevel);

            Assert.False(result);
            Assert.Equal(0, skillLevel);
        }
    }
}
