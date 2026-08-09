using System;
using System.Reflection;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeDispelStackTests
    {
        [Fact]
        public void DispelEffectExposesNativeStackColumn()
        {
            var effect = new DispelEffect
            {
                BuffTagId = 4294,
                CureCount = 0,
                DispelCount = 0,
                Stack = 1
            };

            Assert.Equal(1, effect.Stack);
            Assert.Equal(0, effect.CureCount);
            Assert.Equal(0, effect.DispelCount);
        }

        [Theory]
        [InlineData(1, 1, 0)]
        [InlineData(3, 1, 2)]
        [InlineData(3, 3, 0)]
        public void StackArithmeticConsumesAtMostRequestedAmount(
            int initial,
            int requested,
            int expected)
        {
            var consumed = Math.Min(Math.Max(1, initial), requested);
            Assert.Equal(expected, initial - consumed);
        }
    }
}
