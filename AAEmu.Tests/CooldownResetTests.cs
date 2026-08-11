using AAEmu.Game.Models.Game.Char;
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

        [Fact]
        public void IgnoreCooldownResetDoesNotEmitForZeroCooldownComboRoot()
        {
            var character = new Character(null);

            // Flamebolt 10752 has cooldown_time=0 in the AA8 compact. A GM
            // ignore-cooldowns cleanup must not send 0x098 for the skill or
            // its Combo tag 3308: that packet resets the client chain to the
            // casted first stage and suppresses 24894/24895.
            Assert.False(character.ResetSkillCooldown(10752, false));
            Assert.Empty(character.Cooldowns.Cooldowns);
        }

    }
}
