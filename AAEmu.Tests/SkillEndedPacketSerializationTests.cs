using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class SkillEndedPacketSerializationTests
    {
        [Fact]
        public void Aa8SkillEndedSerializesTransactionId()
        {
            var stream = new PacketStream();

            new SCSkillEndedPacket(0x0556).Write(stream);

            Assert.Equal(new byte[] { 0x56, 0x05 }, stream.GetBytes());
        }

        [Fact]
        public void Aa8SkillEndedDoesNotCollapseTransactionIdToBoolean()
        {
            var stream = new PacketStream();

            new SCSkillEndedPacket(0xFF01).Write(stream);

            Assert.Equal(new byte[] { 0x01, 0xFF }, stream.GetBytes());
        }
    }
}
