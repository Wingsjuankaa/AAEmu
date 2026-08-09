using System.Collections.Generic;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCUnitAiAggroPacket : GamePacket
    {
        private readonly uint _npcId;
        private readonly int _count;
        private readonly uint _hostileUnitId;
        private readonly int _value1;
        private readonly int _value2;
        private readonly int _value3;
        private readonly byte _topFlags;

        public SCUnitAiAggroPacket(uint npcId, int count, uint hostileUnitId = 0, List<int> summarizeDamage = null,
            byte topFlags = 0, byte level = 1) : base(SCOffsets.SCUnitAiAggroPacket, level)
        {
            _npcId = npcId;
            _count = count;
            _hostileUnitId = hostileUnitId;
            // AA8's native reader consumes exactly three int32 values per
            // aggro entry. Copy those scalars at construction time: combat can
            // keep updating the source list without changing a queued packet.
            _value1 = GetValueOrDefault(summarizeDamage, 0);
            _value2 = GetValueOrDefault(summarizeDamage, 1);
            _value3 = GetValueOrDefault(summarizeDamage, 2);
            _topFlags = topFlags;
        }

        /// <summary>
        /// Builds the combat-closure form used by the pre-regression AA8
        /// runtime.  Normal aggro updates are immediate level-1 packets, but
        /// the empty table that closes a lethal transaction travelled in the
        /// ordered DD05 stream.  Keeping the two forms explicit prevents a
        /// static packet-layout result from silently changing transaction
        /// ordering across channels.
        /// </summary>
        public static SCUnitAiAggroPacket CreateCombatClear(uint ownerObjId)
        {
            return new SCUnitAiAggroPacket(ownerObjId, 0, level: 5);
        }

        public static SCUnitAiAggroPacket CreateClear(uint npcObjId)
        {
            return new SCUnitAiAggroPacket(npcObjId, 0);
        }

        private static int GetValueOrDefault(IReadOnlyList<int> values, int index)
        {
            return values != null && index < values.Count ? values[index] : 0;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_npcId);
            stream.Write(_count);

            if (_count <= 0)
                return stream;

            for (var i = 0; i < _count; i++)
            {
                stream.WriteBc(_hostileUnitId);
                stream.Write(_value1);
                stream.Write(_value2);
                stream.Write(_value3);
                stream.Write(_topFlags); // topFlags
            }

            return stream;
        }

        public override string Verbose()
        {
            return $" - npc={_npcId}, count={_count}, hostile={_hostileUnitId}, values=[{_value1},{_value2},{_value3}], topFlags={_topFlags}";
        }
    }
}
