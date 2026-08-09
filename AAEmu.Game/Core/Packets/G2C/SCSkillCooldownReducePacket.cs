using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// AA8 r558734 serializer reconstructed from Stage 15
    /// FUN_39991d60 (opcode 0x038).
    /// </summary>
    public class SCSkillCooldownReducePacket : GamePacket
    {
        private readonly uint _bc;
        private readonly int _skillId;
        private readonly int _tagId;
        private readonly uint _percent;
        private readonly uint _count;
        private readonly uint _reduce;
        private readonly bool _rstc;
        private readonly bool _rtsc;
        private readonly bool _rtstc;

        public SCSkillCooldownReducePacket(
            uint bc,
            int skillId,
            int tagId,
            uint percent,
            uint count,
            uint reduce,
            bool rstc = false,
            bool rtsc = false,
            bool rtstc = false) : base(SCOffsets.SCSkillCooldownReducePacket, 5)
        {
            _bc = bc;
            _skillId = skillId;
            _tagId = tagId;
            _percent = percent;
            _count = count;
            _reduce = reduce;
            _rstc = rstc;
            _rtsc = rtsc;
            _rtstc = rtstc;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_bc);
            stream.Write(_skillId);
            stream.Write(_tagId);
            stream.Write(_percent);
            stream.Write(_count);
            stream.Write(_reduce);
            stream.Write(_rstc);
            stream.Write(_rtsc);
            stream.Write(_rtstc);
            return stream;
        }
    }
}
