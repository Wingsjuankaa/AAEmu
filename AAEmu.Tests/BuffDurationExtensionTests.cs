using AAEmu.Game.Models.Game.Skills;
using Xunit;

namespace AAEmu.Tests
{
    public class BuffDurationExtensionTests
    {
        [Theory]
        [InlineData(20000, 20000, 40000, 40000)]
        [InlineData(5000, 20000, 40000, 25000)]
        [InlineData(30000, 20000, 40000, 40000)]
        [InlineData(5000, 20000, 0, 25000)]
        [InlineData(5000, -1, 40000, 5000)]
        public void ExtendUsesRemainingTimeAndHonorsNativeMaximum(
            int remaining,
            int extension,
            int maximum,
            int expected)
        {
            Assert.Equal(
                expected,
                Buff.CalculateExtendedRemaining(remaining, extension, maximum));
        }
    }
}
