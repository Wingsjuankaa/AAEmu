using System;
using System.Collections.Generic;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class ShadowplayBuffStealTests
    {
        [Theory]
        [InlineData(1, 0, 1)]
        [InlineData(0, 2, 2)]
        [InlineData(0, 3, 3)]
        [InlineData(-1, 0, 0)]
        public void NativeDescriptorGenerationsResolveTransferCount(
            int value1,
            int value3,
            int expected)
        {
            Assert.Equal(expected, BuffSteal.ResolveCount(value1, value3));
        }

        [Fact]
        public void WeightedLeechDescriptorsSelectExactlyOneOutcome()
        {
            var stealTwo = new SkillEffect {EffectId = 7433, Weight = 1};
            var stealThree = new SkillEffect {EffectId = 67458, Weight = 1};
            var effects = new[] {stealTwo, stealThree};

            Assert.Same(stealTwo, Skill.SelectWeightedEffect(effects, 0));
            Assert.Same(stealThree, Skill.SelectWeightedEffect(effects, 1));
            Assert.Null(Skill.SelectWeightedEffect(effects, 2));
        }

        [Fact]
        public void OnlyActiveDispellableGoodBuffsAreEligible()
        {
            var eligible = MakeBuff(42);
            var required = new HashSet<uint> {42};

            Assert.True(Buffs.IsStealableGoodBuff(eligible));
            Assert.True(Buffs.IsStealableGoodBuff(eligible, required));
            Assert.False(Buffs.IsStealableGoodBuff(eligible, new HashSet<uint> {99}));
            Assert.False(Buffs.IsStealableGoodBuff(MakeBuff(42, system: true)));
            Assert.False(Buffs.IsStealableGoodBuff(MakeBuff(42, ownerOnly: true)));
            Assert.False(Buffs.IsStealableGoodBuff(MakeBuff(42, exempt: true)));

            eligible.Passive = true;
            Assert.False(Buffs.IsStealableGoodBuff(eligible));
        }

        private static Buff MakeBuff(
            uint id,
            bool system = false,
            bool ownerOnly = false,
            bool exempt = false)
        {
            return new Buff(
                new Unit(),
                new Unit(),
                null,
                new BuffTemplate
                {
                    Id = id,
                    Kind = BuffKind.Good,
                    System = system,
                    OwnerOnly = ownerOnly,
                    Exempt = exempt,
                },
                null,
                DateTime.UtcNow)
            {
                InUse = true,
            };
        }
    }
}
