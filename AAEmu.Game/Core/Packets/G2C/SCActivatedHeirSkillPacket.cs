using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public sealed class SCActivatedHeirSkillPacket : GamePacket
    {
        private readonly int _heirSkillId;
        private readonly int _successorSkillId;
        private readonly bool _isChange;

        public SCActivatedHeirSkillPacket(int heirSkillId, int successorSkillId, bool isChange)
            : base(SCOffsets.SCActivatedHeirSkillPacket, 5)
        {
            _heirSkillId = heirSkillId;
            _successorSkillId = successorSkillId;
            _isChange = isChange;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_heirSkillId);
            stream.Write(_successorSkillId);
            stream.Write(_isChange);
            return stream;
        }
    }
}
