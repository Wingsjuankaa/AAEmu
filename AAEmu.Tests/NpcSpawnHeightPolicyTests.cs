using AAEmu.Game.Models.Game.NPChar;
using Xunit;

namespace AAEmu.Tests
{
    public class NpcSpawnHeightPolicyTests
    {
        [Fact]
        public void CorrectsOrdinaryGroundNpcWithinOneMeter()
        {
            Assert.Equal(12.6f, NpcSpawnHeightPolicy.Resolve(13.2f, 12.6f, true, false));
        }

        [Theory]
        [InlineData(13.6f, 12.6f)]
        [InlineData(15f, 12.6f)]
        public void PreservesElevatedSpawnAtOrBeyondOneMeter(float source, float terrain)
        {
            Assert.Equal(source, NpcSpawnHeightPolicy.Resolve(source, terrain, true, false));
        }

        [Fact]
        public void PreservesFlyingNpc()
        {
            Assert.Equal(13.2f, NpcSpawnHeightPolicy.Resolve(13.2f, 12.6f, true, true));
        }

        [Fact]
        public void PreservesSourceWhenHeightMapIsUnavailable()
        {
            Assert.Equal(13.2f, NpcSpawnHeightPolicy.Resolve(13.2f, 0f, false, false));
        }
    }
}
