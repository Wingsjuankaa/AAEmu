using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.StaticValues;
using Xunit;

namespace AAEmu.Tests
{
    public class GamePointPacketTests
    {
        [Fact]
        public void InitedSerializesAa8KindAndPoint()
        {
            var stream = new PacketStream();
            var packet = new SCGamePointInitedPacket(
                (byte)GamePointKind.Honor,
                310000);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x00, 0xF0, 0xBA, 0x04, 0x00 },
                stream.GetBytes());
        }

        [Fact]
        public void ChangedSerializesAa8CountKindAndPositiveAmount()
        {
            var stream = new PacketStream();
            var packet = new SCGamePointChangedPacket(
                (byte)GamePointKind.Honor,
                50000);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x01, 0x00, 0x50, 0xC3, 0x00, 0x00 },
                stream.GetBytes());
        }

        [Fact]
        public void ChangedPreservesSignedPurchaseDebit()
        {
            var stream = new PacketStream();
            var packet = new SCGamePointChangedPacket(
                (byte)GamePointKind.Honor,
                -10000);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x01, 0x00, 0xF0, 0xD8, 0xFF, 0xFF },
                stream.GetBytes());
        }
    }
}
