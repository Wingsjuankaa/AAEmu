using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class ChatBubblePacketTests
    {
        [Fact]
        public void Aa8LocalizedBubbleUsesNativeIdPayload()
        {
            var packet = new SCChatBubblePacket(0x010203, 3, 2, 7542, string.Empty);

            Assert.Equal(5, packet.Level);

            var stream = new PacketStream();
            packet.Write(stream);

            stream.Pos = 0;
            Assert.Equal(0x010203u, stream.ReadBc());
            Assert.Equal(3, stream.ReadByte());
            Assert.Equal(2, stream.ReadByte());
            Assert.Equal(7542u, stream.ReadUInt32());
            Assert.Equal(stream.Count, stream.Pos);
        }

        [Fact]
        public void Aa8LiteralBubbleUsesStringPayload()
        {
            var packet = new SCChatBubblePacket(7, 1, 1, 0, "AA8");

            Assert.Equal(5, packet.Level);

            var stream = new PacketStream();
            packet.Write(stream);

            stream.Pos = 0;
            Assert.Equal(7u, stream.ReadBc());
            Assert.Equal(1, stream.ReadByte());
            Assert.Equal(1, stream.ReadByte());
            Assert.Equal("AA8", stream.ReadString());
            Assert.Equal(stream.Count, stream.Pos);
        }
    }
}
