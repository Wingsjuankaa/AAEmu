using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
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

        [Fact]
        public void UsedSkillPoints_ExcludeNativeDefaultSkills()
        {
            var skills = new CharacterSkills(null);
            skills.Skills.Add(18132, CreateSkill(18132, 1, true));
            skills.Skills.Add(35418, CreateSkill(35418, 1, false));
            skills.Skills.Add(35420, CreateSkill(35420, 1, false));

            Assert.Equal(1, skills.GetUsedSkillPoints());
            Assert.Equal(1, skills.GetUsedSkillPoints((byte)AbilityType.Fight));
        }

        [Fact]
        public void NonLearnableNativeDefaultSkill_CannotEnterLearnedSkillSet()
        {
            var skills = new CharacterSkills(null);
            var template = new SkillTemplate
            {
                Id = 35418,
                AbilityId = (byte)AbilityType.General,
                SkillPoints = 1,
                NeedLearn = false
            };

            Assert.False(skills.AddSkill(template, 1, false));
            Assert.Empty(skills.Skills);
        }

        private static Skill CreateSkill(
            uint id,
            int skillPoints,
            bool needLearn)
        {
            var template = new SkillTemplate
            {
                Id = id,
                AbilityId = needLearn
                    ? (byte)AbilityType.Fight
                    : (byte)AbilityType.General,
                SkillPoints = skillPoints,
                NeedLearn = needLearn
            };
            return new Skill
            {
                Id = id,
                Level = 1,
                Template = template
            };
        }
    }
}
