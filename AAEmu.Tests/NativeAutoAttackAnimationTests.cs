using AAEmu.Game.Models.Game.Items;
using Xunit;

namespace AAEmu.Tests
{
    public class NativeAutoAttackAnimationTests
    {
        private static readonly Holdable NuianStarterSword = new Holdable
        {
            AnimRight1Ratio = 50,
            AnimRight1Id = 87,
            AnimRight2Ratio = 50,
            AnimRight2Id = 3,
            AnimRight3Id = 87
        };

        [Theory]
        [InlineData(0, 87)]
        [InlineData(49, 87)]
        [InlineData(50, 3)]
        [InlineData(99, 3)]
        public void SelectsNativeWeightedRightHandAnimation(int roll, uint expected)
        {
            Assert.Equal(expected, NuianStarterSword.SelectRightAttackAnimation(roll));
        }

        [Fact]
        public void UsesThirdAnimationAsNativeFallback()
        {
            var holdable = new Holdable { AnimRight3Id = 91 };
            Assert.Equal(91u, holdable.SelectRightAttackAnimation(50));
        }
    }
}
