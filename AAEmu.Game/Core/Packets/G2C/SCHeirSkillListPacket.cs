using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public struct HeirSkillListEntry
    {
        public int HeirSkillId;
        public int BaseSkillId;
        public int SuccessorSkillId;
        public uint SkillLevel;
        public sbyte Ability;
        public sbyte ActiveType;
    }

    /// <summary>AA8 FUN_399a6650/FUN_399210e0: count + 18-byte entries, maximum 128.</summary>
    public sealed class SCHeirSkillListPacket : GamePacket
    {
        public const int MaxEntries = 128;
        private readonly HeirSkillListEntry[] _entries;

        public SCHeirSkillListPacket(IEnumerable<HeirSkillListEntry> entries)
            : base(SCOffsets.SCHeirSkillListPacket, 5)
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
                stream.Write(entry.HeirSkillId);
                stream.Write(entry.BaseSkillId);
                stream.Write(entry.SuccessorSkillId);
                stream.Write(entry.SkillLevel);
                stream.Write(entry.Ability);
                stream.Write(entry.ActiveType);
            }
            return stream;
        }
    }
}
