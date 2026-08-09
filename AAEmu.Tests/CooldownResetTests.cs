using AAEmu.Game.Models.Game.Skills.Templates;

using Xunit;

namespace AAEmu.Tests
{
    public class CooldownResetTests
    {
        [Fact]
        public void NativeCooldownTagsExcludeZeroAndDuplicates()
        {
            var template = new SkillTemplate
            {
                CooldownTagId = 4156,
                SecondCooldownTagId = 0,
                ThirdCooldownTagId = 4156
            };

            Assert.Equal(new uint[] {4156}, template.GetCooldownTagIds());
        }

        [Fact]
        public void NativeCooldownTagsPreserveAllConfirmedGroups()
        {
            var template = new SkillTemplate
            {
                CooldownTagId = 4156,
                SecondCooldownTagId = 3291,
                ThirdCooldownTagId = 3292
            };

            Assert.Equal(new uint[] {4156, 3291, 3292}, template.GetCooldownTagIds());
        }
    }
}
