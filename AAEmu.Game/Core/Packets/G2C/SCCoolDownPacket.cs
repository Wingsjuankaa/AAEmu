using System.Collections.Generic;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCCooldownsPacket : GamePacket
    {
        private readonly IReadOnlyList<CooldownSnapshotEntry> _skills;

        public SCCooldownsPacket(Character character) : base(SCOffsets.SCCooldownsPacket, 5)
        {
            _skills = character?.Cooldowns.GetSnapshot(MechanicsRuntime.UtcNow) ??
                new List<CooldownSnapshotEntry>();
        }

        public override PacketStream Write(PacketStream stream)
        {
            // AA8 Stage 15 FUN_39985ee0: three bounded (150) buckets,
            // each entry being id/duration/remaining as 32-bit values.
            stream.Write((uint)_skills.Count);
            foreach (var cooldown in _skills)
            {
                stream.Write(cooldown.SkillId);
                stream.Write((uint)cooldown.DurationMilliseconds);
                stream.Write((uint)cooldown.RemainingMilliseconds);
            }
            stream.Write(0u); // cooldown-tag bucket
            stream.Write(0u); // charge bucket
            return stream;
        }
    }
}
