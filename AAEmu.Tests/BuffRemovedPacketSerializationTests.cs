using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class BuffRemovedPacketSerializationTests
    {
        [Theory]
        [InlineData((byte)0)]
        [InlineData((byte)7)]
        public void Aa8BuffRemovedIncludesNativeReasonByte(byte reason)
        {
            const uint objId = 0x10203040;
            const uint buffIndex = 0x50607080;

            var expected = new PacketStream();
            expected.WriteBc(objId);
            expected.Write(buffIndex);
            expected.Write(reason);

            var actual = new SCBuffRemovedPacket(objId, buffIndex, reason)
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal(expected.GetBytes(), actual);
        }
    }
}
