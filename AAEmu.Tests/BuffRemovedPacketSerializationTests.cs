using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class BuffRemovedPacketSerializationTests
    {
        [Fact]
        public void Aa8BuffRemovedUsesNativeTwoFieldLayout()
        {
            const uint objId = 0x10203040;
            const uint buffIndex = 0x50607080;

            var expected = new PacketStream();
            expected.WriteBc(objId);
            expected.Write(buffIndex);

            var actual = new SCBuffRemovedPacket(objId, buffIndex)
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal(expected.GetBytes(), actual);
            Assert.Equal(7, actual.Length);
        }
    }
}
