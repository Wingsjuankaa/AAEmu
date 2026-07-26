using System;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeRegionRemovalProtocolTests
    {
        [Fact]
        public void UnitsRemovedUsesExactAa8OpcodeAndGoldenPayload()
        {
            var packet = new SCUnitsRemovedPacket(new uint[]
            {
                0x000001,
                0x112233,
                0xABCDEF
            });

            Assert.Equal(0x230, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                new byte[]
                {
                    0x03, 0x00,
                    0x01, 0x00, 0x00,
                    0x33, 0x22, 0x11,
                    0xEF, 0xCD, 0xAB
                },
                packet.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void UnitsRemovedRejectsMoreThanTheNative500Entries()
        {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => new SCUnitsRemovedPacket(
                    Enumerable.Repeat(1u, SCUnitsRemovedPacket.MaxCountPerPacket + 1)
                        .ToArray()));
        }

        [Fact]
        public void DoodadRemovedUsesExactAa8OpcodeAndGoldenPayload()
        {
            var packet = new SCDoodadRemovedPacket(0x112233);

            Assert.Equal(0x031, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                new byte[] { 0x33, 0x22, 0x11, 0x00 },
                packet.Write(new PacketStream()).GetBytes());
        }
    }
}
