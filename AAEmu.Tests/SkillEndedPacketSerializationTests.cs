using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class SkillEndedPacketSerializationTests
    {
        [Fact]
        public void Aa8SkillEndedSerializesCompletedBooleanOnly()
        {
            var stream = new PacketStream();

            new SCSkillEndedPacket().Write(stream);

            Assert.Equal(new byte[] { 1 }, stream.GetBytes());
        }

        [Fact]
        public void Aa8SkillEndedCanSerializeIncompleteState()
        {
            var stream = new PacketStream();

            new SCSkillEndedPacket(false).Write(stream);

            Assert.Equal(new byte[] { 0 }, stream.GetBytes());
        }
    }
}
