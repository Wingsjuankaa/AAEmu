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
        public void AbilitySwapSerializesOneChangeAndTwoNativeTerminators()
        {
            var stream = new PacketStream();
            var packet = new SCAbilitySwappedPacket(
                32316,
                AbilityType.Fight,
                AbilityType.Magic);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x3C, 0x7E, 0x00, 0x01, 0x07, 0x1E, 0x1E, 0x1E, 0x1E },
                stream.GetBytes());
        }

        [Fact]
        public void SpecialAbilityActivationSerializesActiveAbility()
        {
            var stream = new PacketStream();
            var packet = new SCSpecialAbilityActivedPacket(AbilityType.Adamant);

            packet.Write(stream);

            Assert.Equal(new byte[] { 0x03 }, stream.GetBytes());
        }

        [Fact]
        public void FirstAbilityActivationUsesLowerOfCharacterAndLevelFifteenExp()
        {
            var method = typeof(AAEmu.Game.Models.Game.Char.CharacterAbilities).GetMethod(
                "CalculateInitialAbilityExp",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(method);
            Assert.Equal(133000, method.Invoke(null, new object[] { 7784000, 133000 }));
            Assert.Equal(42000, method.Invoke(null, new object[] { 42000, 133000 }));
            Assert.Equal(0, method.Invoke(null, new object[] { -1, 133000 }));
        }

        [Fact]
        public void AbilityExpChangedSerializesNativeApplyAllFlag()
        {
            var stream = new PacketStream();
            var packet = new SCAbilityExpChangedPacket(32316, AbilityType.Adamant, 133000, false);

            packet.Write(stream);

            Assert.Equal(
                new byte[] { 0x3C, 0x7E, 0x00, 0x03, 0x88, 0x07, 0x02, 0x00, 0x00 },
                stream.GetBytes());
        }
    }
}
