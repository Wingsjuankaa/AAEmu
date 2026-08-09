using System.Collections.Generic;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using Xunit;

namespace AAEmu.Tests
{
    public class UnitAiAggroPacketTests
    {
        [Fact]
        public void SerializationUsesConstructionTimeDamageSnapshot()
        {
            var liveDamage = new List<int> { 30, 45, 60 };
            var packet = new SCUnitAiAggroPacket(100, 1, 200, liveDamage);

            liveDamage.Clear();
            liveDamage.Add(999);

            var actual = packet.Write(new PacketStream()).GetBytes();
            var expected = new SCUnitAiAggroPacket(
                    100, 1, 200, new List<int> { 30, 45, 60 })
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal(expected, actual);
        }

        [Fact]
        public void UsesImmediateChannelAndWritesExactlyThreeAggroValues()
        {
            var packet = new SCUnitAiAggroPacket(
                100, 1, 200, new List<int> { 30, 45, 60, 999 });

            var actual = packet.Write(new PacketStream()).GetBytes();
            var expected = new SCUnitAiAggroPacket(
                    100, 1, 200, new List<int> { 30, 45, 60 })
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal((byte)1, packet.Level);
            Assert.Equal(expected, actual);
        }

        [Fact]
        public void DamageAggroUsesNoTopFlagsUnlessExplicitlyRequested()
        {
            var defaultPacket = new SCUnitAiAggroPacket(
                100, 1, 200, new List<int> { 30, 45, 60 });
            var flaggedPacket = new SCUnitAiAggroPacket(
                100, 1, 200, new List<int> { 30, 45, 60 }, 135);

            var defaultBytes = defaultPacket.Write(new PacketStream()).GetBytes();
            var flaggedBytes = flaggedPacket.Write(new PacketStream()).GetBytes();

            Assert.Equal((byte)0, defaultBytes[defaultBytes.Length - 1]);
            Assert.Equal((byte)135, flaggedBytes[flaggedBytes.Length - 1]);
        }

        [Fact]
        public void VerboseTraceExposesTheCompleteAggroEntry()
        {
            var packet = new SCUnitAiAggroPacket(
                100, 1, 200, new List<int> { 30, 45, 60 });

            Assert.Equal(
                " - npc=100, count=1, hostile=200, values=[30,45,60], topFlags=0",
                packet.Verbose());
        }

        [Fact]
        public void EmptyAggroTableSerializesOnlyOwnerAndZeroCount()
        {
            var packet = SCUnitAiAggroPacket.CreateClear(57159);
            var actual = packet.Write(new PacketStream()).GetBytes();

            Assert.Equal(
                new byte[] { 0x47, 0xDF, 0x00, 0x00, 0x00, 0x00, 0x00 },
                actual);
            Assert.Equal(" - npc=57159, count=0, hostile=0, values=[0,0,0], topFlags=0", packet.Verbose());
        }

        [Fact]
        public void LethalCombatClearUsesTheHistoricalOrderedChannel()
        {
            var packet = SCUnitAiAggroPacket.CreateCombatClear(57159);

            Assert.Equal((byte)5, packet.Level);
            Assert.Equal(
                SCUnitAiAggroPacket.CreateClear(57159).Write(new PacketStream()).GetBytes(),
                packet.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void NpcInteractionClearUsesTheAa8OrderedChannel()
        {
            var packet = SCUnitAiAggroPacket.CreateInteractionClear(57159);

            Assert.Equal((byte)5, packet.Level);
            Assert.Equal(
                SCUnitAiAggroPacket.CreateClear(57159).Write(new PacketStream()).GetBytes(),
                packet.Write(new PacketStream()).GetBytes());
        }
    }
}
