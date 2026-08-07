using AAEmu.Game.Core.Packets.C2G;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeRespawnProtocolTests
    {
        [Fact]
        public void ResurrectCharacterUsesObservedAa8OpcodeAndLevel()
        {
            var packet = new CSResurrectCharacterPacket();

            Assert.Equal(0x1E5, packet.TypeId);
            Assert.Equal(5, packet.Level);
        }
    }
}
