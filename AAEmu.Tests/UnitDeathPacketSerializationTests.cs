using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Models.Mechanics;

using System.Collections.Generic;
using System.Linq;

using Xunit;

namespace AAEmu.Tests
{
    public class UnitDeathPacketSerializationTests
    {
        [Fact]
        public void Aa8DeathWithoutKillerMatchesLastKnownGoodWireBody()
        {
            var expected = BuildExpected(0x123456, KillReason.Damage, null);
            var actual = new SCUnitDeathPacket(0x123456, KillReason.Damage)
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal(20, actual.Length);
            Assert.Equal(expected, actual);
        }

        [Fact]
        public void Aa8DeathWithKillerMatchesLastKnownGoodConditionalBranch()
        {
            var killer = new Unit {ObjId = 0x654321, Name = "Dannia"};
            var expected = BuildExpected(0x123456, KillReason.Damage, killer);
            var actual = new SCUnitDeathPacket(0x123456, KillReason.Damage, killer)
                .Write(new PacketStream())
                .GetBytes();

            Assert.Equal(34, actual.Length);
            Assert.Equal(expected, actual);
        }

        [Fact]
        public void NonCharacterDeathPreservesCausalKillerMetadata()
        {
            // Use a self-caused non-Character death so the test remains
            // independent from ItemManager while still guarding the former
            // `this is Character ? killer : null` regression.
            var victim = new RecordingUnit {ObjId = 0x123456, Name = "NpcLike"};

            victim.DoDie(victim, KillReason.Damage);

            var death = Assert.Single(victim.Packets.OfType<SCUnitDeathPacket>());
            var expected = BuildExpected(victim.ObjId, KillReason.Damage, victim);
            Assert.Equal(expected, death.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void Aa8LethalCombatClosureMatchesLastKnownGoodTransaction()
        {
            var victim = new RecordingUnit {ObjId = 0x123456, Name = "NpcLike"};
            var killer = new RecordingUnit {ObjId = 0x654321, Name = "Dannia"};
            victim.CurrentTarget = killer;
            killer.CurrentTarget = victim;

            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {SuppressLoot = true}))
                victim.DoDie(killer, KillReason.Damage);

            Assert.Collection(killer.Packets,
                packet => Assert.IsType<SCUnitDeathPacket>(packet),
                packet => Assert.Equal(
                    WriteBody(SCUnitAiAggroPacket.CreateCombatClear(killer.ObjId)),
                    WriteBody(Assert.IsType<SCUnitAiAggroPacket>(packet))),
                packet => Assert.Equal(
                    WriteBody(new SCCombatClearedPacket(victim.ObjId)),
                    WriteBody(Assert.IsType<SCCombatClearedPacket>(packet))),
                packet => Assert.Equal(
                    WriteBody(new SCCombatClearedPacket(killer.ObjId)),
                    WriteBody(Assert.IsType<SCCombatClearedPacket>(packet))),
                packet => Assert.IsType<SCTargetChangedPacket>(packet));
            Assert.Null(killer.CurrentTarget);
        }

        private static byte[] WriteBody(GamePacket packet)
        {
            return packet.Write(new PacketStream()).GetBytes();
        }

        private static byte[] BuildExpected(uint victimId, KillReason reason, Unit killer)
        {
            var stream = new PacketStream();
            stream.WriteBc(victimId);
            stream.Write((byte)reason);
            stream.Write(0u); // resurrectionWaitingTime
            stream.Write(0u); // specialResurrectionWaitingTime
            stream.Write(0);  // lostExp
            stream.Write((byte)0);
            stream.WriteBc(killer?.ObjId ?? 0);
            if (killer == null)
                return stream.GetBytes();

            stream.Write((byte)0);   // GameType
            stream.Write((ushort)0); // killStreak
            stream.Write((byte)0);   // param1
            stream.Write((byte)0);   // param2
            stream.Write((byte)0);   // type, u8 in the observed AA8 wire body
            stream.Write(killer.Name, true, false);
            return stream.GetBytes();
        }

        private sealed class RecordingUnit : Unit
        {
            public List<GamePacket> Packets { get; } = new List<GamePacket>();

            public override void BroadcastPacket(GamePacket packet, bool self)
            {
                Packets.Add(packet);
            }
        }
    }
}
