using System.Reflection;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using Xunit;

namespace AAEmu.Tests
{
    public class UnitStateSerializationTests
    {
        [Fact]
        public void LearnedSkillsSharePiscHeaderWithinGroup()
        {
            var stream = new PacketStream();
            var writer = typeof(SCUnitStatePacket).GetMethod(
                "WritePiscValues",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(writer);
            writer.Invoke(null, new object[] { stream, new long[] { 18132, 11918 } });

            Assert.Equal(new byte[] { 0x05, 0xD4, 0x46, 0x8E, 0x2E }, stream.GetBytes());
        }

        [Fact]
        public void AbilitySwapRepeatsRequestedPairForThreeSlots()
        {
            var stream = new PacketStream();
            var packet = new SCAbilitySwappedPacket(
                32316, AbilityType.None, AbilityType.Vocation);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x3C, 0x7E, 0x00, 0x1E, 0x08, 0x1E, 0x08, 0x1E, 0x08 },
                stream.GetBytes());
        }
    }
}
