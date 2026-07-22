using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.World.Transform;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotEventPacketTests
    {
        [Fact]
        public void EightZeroPositionPlotObjectWritesCompleteLayout()
        {
            var position = new Transform(null, null, 10.25f, 20.5f, 30.75f, 0.1f, 0.2f, 0.3f);
            var stream = new PacketStream();

            new PlotObject(position).Write(stream);

            // type + (position[11] + rotation[3]) * 2 + three BC3 ids
            Assert.Equal(38, stream.Count);
            Assert.Equal((byte)PlotObjectType.POSITION, stream[0]);

            // A point target is encoded as a degenerate line at the same
            // position, so both native Kakao 8 positional blocks are equal.
            for (var i = 0; i < 14; i++)
                Assert.Equal(stream[1 + i], stream[15 + i]);

            for (var i = 29; i < 38; i++)
                Assert.Equal(0, stream[i]);
        }

        [Fact]
        public void EightZeroUnitPlotObjectKeepsLegacyCompactLayout()
        {
            var stream = new PacketStream();

            new PlotObject(11).Write(stream);

            Assert.Equal(4, stream.Count);
            Assert.Equal((byte)PlotObjectType.UNIT, stream[0]);
            Assert.Equal(11, stream[1]);
            Assert.Equal(0, stream[2]);
            Assert.Equal(0, stream[3]);
        }

        [Fact]
        public void EightZeroPlotEventAlwaysEndsWithInputDirection()
        {
            var stream = new PacketStream();
            var packet = new SCPlotEventPacket(
                7, 37718, 40331,
                new PlotObject(11), new PlotObject(12),
                0, 0, 2, 0x5A);

            packet.Write(stream);

            Assert.Equal(0x5A, stream[stream.Count - 1]);
        }

        [Fact]
        public void EightZeroPlotEventWritesInputDirectionAfterOptionalFlagBlock()
        {
            var stream = new PacketStream();
            var packet = new SCPlotEventPacket(
                7, 37718, 40331,
                new PlotObject(11), new PlotObject(12),
                0, 0, 8, 0xA5);

            packet.Write(stream);

            Assert.Equal(0xA5, stream[stream.Count - 1]);
            for (var i = stream.Count - 1 - (13 * sizeof(int)); i < stream.Count - 1; i++)
                Assert.Equal(0, stream[i]);
        }
    }
}
