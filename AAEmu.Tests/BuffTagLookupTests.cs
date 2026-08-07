using System;
using System.Collections.Generic;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class BuffTagLookupTests
    {
        [Fact]
        public void MissingNativeTagIsAnEmptyMembershipSet()
        {
            var effects = new List<Buff>
            {
                null,
                new Buff(null, null, null, null, null, DateTime.UtcNow)
            };

            Assert.False(Buffs.ContainsBuffWithTag(effects, null));
            Assert.False(Buffs.ContainsBuffWithTag(effects, new List<uint>()));
        }

        [Fact]
        public void TagLookupIgnoresIncompleteEffectsAndMatchesLoadedTemplate()
        {
            var effects = new List<Buff>
            {
                new Buff(null, null, null, null, null, DateTime.UtcNow),
                new Buff(
                    null,
                    null,
                    null,
                    new BuffTemplate { Id = 42 },
                    null,
                    DateTime.UtcNow)
            };

            Assert.False(Buffs.ContainsBuffWithTag(effects, new List<uint> { 1 }));
            Assert.True(Buffs.ContainsBuffWithTag(effects, new List<uint> { 42 }));
        }

        [Fact]
        public void NativeBuffTagStackRangeCountsMultipleInstancesAndStackUnits()
        {
            var template = new BuffTemplate { Id = 24495 };
            var effects = new List<Buff>
            {
                new Buff(null, null, null, template, null, DateTime.UtcNow)
                {
                    InUse = true,
                    Stack = 2
                },
                new Buff(null, null, null, template, null, DateTime.UtcNow)
                {
                    InUse = true,
                    Stack = 1
                },
                new Buff(null, null, null, template, null, DateTime.UtcNow)
                {
                    InUse = false,
                    Stack = 5
                }
            };

            Assert.Equal(3, Buffs.CountBuffStacks(effects, new List<uint> { 24495 }));
            Assert.Equal(0, Buffs.CountBuffStacks(effects, new List<uint> { 1 }));
        }
    }
}
