using System;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class SorceryAbsorptionRuntimeTests
    {
        [Fact]
        public void ExhaustingChargeRaisesAbsorptionExactlyOnceAndReturnsOverflow()
        {
            var owner = new Unit();
            var attacker = new Unit();
            var buff = new Buff(owner, owner, null, new BuffTemplate(), null, DateTime.UtcNow)
            {
                Charge = 100,
                State = EffectState.Created
            };
            var calls = 0;
            OnAbsorptionArgs observed = null;
            buff.Events.OnAbsorption += (_, args) =>
            {
                calls++;
                observed = (OnAbsorptionArgs)args;
            };

            Assert.Equal(0, buff.ConsumeCharge(40, attacker));
            Assert.Equal(60, buff.Charge);
            Assert.Equal(0, calls);
            Assert.Equal(15, buff.ConsumeCharge(75, attacker));
            Assert.Equal(0, buff.Charge);
            Assert.Equal(1, calls);
            Assert.Same(attacker, observed.Source);
            Assert.Same(owner, observed.Target);
            Assert.Equal(60, observed.Amount);
            Assert.Equal(5, buff.ConsumeCharge(5, attacker));
            Assert.Equal(1, calls);
        }

        [Fact]
        public void BuffEndStartsItsDeferredSkillCooldown()
        {
            var owner = new Unit();

            Assert.True(BuffTemplate.StartDelayedCooldown(owner, owner, 10153, 30000, false));
            Assert.True(owner.Cooldowns.CheckCooldown(10153));
        }

        [Theory]
        [InlineData(0, 30000, false)]
        [InlineData(10153, 0, false)]
        [InlineData(10153, 30000, true)]
        public void InvalidOrReplacementEndDoesNotStartCooldown(
            uint skillId, int duration, bool replaced)
        {
            var owner = new Unit();

            Assert.False(BuffTemplate.StartDelayedCooldown(
                owner, owner, skillId, duration, replaced));
            Assert.False(owner.Cooldowns.CheckCooldown(10153));
        }
    }
}
