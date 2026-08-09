using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public struct SkillActiveTypeEntry
    {
        public int HeirSkillType;
        public int SkillType;
        public byte ActiveType;
    }

    /// <summary>AA8 FUN_39981860/FUN_399236b0: count + 9-byte entries, maximum 200.</summary>
    public sealed class SCListSkillActiveTypsPacket : GamePacket
    {
        public const int MaxEntries = 200;
        private readonly SkillActiveTypeEntry[] _entries;

        public SCListSkillActiveTypsPacket(IEnumerable<SkillActiveTypeEntry> entries)
            : base(SCOffsets.SCListSkillActiveTypsPacket, 5)
        {
            if (entries == null)
                throw new ArgumentNullException(nameof(entries));
            _entries = entries.ToArray();
            if (_entries.Length > MaxEntries)
                throw new ArgumentOutOfRangeException(nameof(entries));
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((uint)_entries.Length);
            foreach (var entry in _entries)
            {
                stream.Write(entry.HeirSkillType);
                stream.Write(entry.SkillType);
                stream.Write(entry.ActiveType);
            }
            return stream;
        }
    }
}
