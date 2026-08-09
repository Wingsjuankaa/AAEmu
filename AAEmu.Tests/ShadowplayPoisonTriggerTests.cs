using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class ShadowplayPoisonTriggerTests
    {
        [Theory]
        [InlineData(DamageType.Melee, 1, true)]
        [InlineData(DamageType.Ranged, 1, true)]
        [InlineData(DamageType.Melee, 0, false)]
        [InlineData(DamageType.Ranged, -1, false)]
        [InlineData(DamageType.Magic, 1, false)]
        [InlineData(DamageType.Siege, 1, false)]
        [InlineData(DamageType.Heal, 1, false)]
        public void PoisonedWeaponsOnlyProcsOnSuccessfulWeaponDamage(
            DamageType damageType,
            int amount,
            bool expected)
        {
            var args = new OnAttackArgs
            {
                DamageType = damageType,
                Amount = amount
            };

            Assert.Equal(expected, AttackBuffTrigger.IsSuccessfulWeaponHit(args));
        }
    }
}
