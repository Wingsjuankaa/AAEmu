using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class ShadowplayPoisonTriggerTests
    {
        [Theory]
        [InlineData(DamageType.Melee, 1, false, true)]
        [InlineData(DamageType.Ranged, 1, false, true)]
        [InlineData(DamageType.Melee, 1, true, false)]
        [InlineData(DamageType.Ranged, 1, true, false)]
        [InlineData(DamageType.Melee, 0, false, false)]
        [InlineData(DamageType.Ranged, -1, false, false)]
        [InlineData(DamageType.Magic, 1, false, false)]
        [InlineData(DamageType.Siege, 1, false, false)]
        [InlineData(DamageType.Heal, 1, false, false)]
        public void PoisonedWeaponsOnlyProcsOnSuccessfulWeaponDamage(
            DamageType damageType,
            int amount,
            bool isPeriodicEffect,
            bool expected)
        {
            var args = new OnAttackArgs
            {
                DamageType = damageType,
                Amount = amount,
                IsPeriodicEffect = isPeriodicEffect
            };

            const int meleeAndRanged = (1 << (int)DamageType.Melee) |
                                       (1 << (int)DamageType.Ranged);
            Assert.Equal(
                expected,
                AttackBuffTrigger.IsSuccessfulHit(args, meleeAndRanged, true));
        }

        [Fact]
        public void ServerTriggeredDamageCannotRecursivelyProcAHitRelation()
        {
            var args = new OnAttackArgs
            {
                DamageType = DamageType.Melee,
                Amount = 10,
                IsTriggeredEffect = true
            };

            Assert.False(AttackBuffTrigger.IsSuccessfulHit(
                args,
                1 << (int)DamageType.Melee,
                true));
        }
    }
}
