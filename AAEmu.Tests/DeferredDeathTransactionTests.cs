using System.Collections.Generic;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;

using Xunit;

namespace AAEmu.Tests
{
    public class SynchronousDeathTransactionTests
    {
        [Fact]
        public void LethalReductionFinalizesDeathBeforePublishingZeroPoints()
        {
            var attacker = new Unit();
            var target = new RecordingUnit {Hp = 100};

            target.ReduceCurrentHp(attacker, 100, KillReason.Damage);

            Assert.Equal(0, target.Hp);
            Assert.Equal(new[] {"death", "points"}, target.EventsSeen);
        }

        [Fact]
        public void CompressedDamageBatchHasNoAuthoritativePostSendQueue()
        {
            Assert.Null(typeof(CompressedGamePackets).GetMethod("AddPostSendAction"));
            Assert.Null(typeof(CompressedGamePackets).GetMethod("ExecutePostSendActions"));
        }

        private sealed class RecordingUnit : Unit
        {
            public List<string> EventsSeen { get; } = new List<string>();

            public override void DoDie(Unit killer, KillReason killReason)
            {
                EventsSeen.Add("death");
            }

            public override void BroadcastPacket(GamePacket packet, bool self)
            {
                if (packet is SCUnitPointsPacket)
                    EventsSeen.Add("points");
            }
        }
    }
}
