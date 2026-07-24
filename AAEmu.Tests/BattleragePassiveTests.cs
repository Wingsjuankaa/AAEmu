using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;

using Xunit;

namespace AAEmu.Tests
{
    public class BattleragePassiveTests
    {
        [Theory]
        [InlineData(true, true, false, true)]
        [InlineData(true, false, true, true)]
        [InlineData(true, false, false, false)]
        [InlineData(false, true, true, false)]
        public void WeaponTrainingAllowsRangedParryWithNativeWeaponConditions(
            bool hasWeaponTraining,
            bool hasDualWield,
            bool hasTwoHanded,
            bool expected)
        {
            Assert.Equal(
                expected,
                Skill.CanParryRangedAttack(
                    hasWeaponTraining,
                    hasDualWield,
                    hasTwoHanded));
        }

        [Fact]
        public void PassiveProcMatchesOnlyItsConfirmedTriggerAndSkillTag()
        {
            var template = new PassiveProcTemplate
            {
                TriggerKind = PassiveProcTriggerKind.DamageSkillHit,
                SkillTagId = 415
            };

            Assert.True(
                template.Matches(
                    PassiveProcTriggerKind.DamageSkillHit,
                    new uint[] {415, 2479}));
            Assert.False(
                template.Matches(
                    PassiveProcTriggerKind.DamageSkillHit,
                    new uint[] {1476}));
        }
    }
}
