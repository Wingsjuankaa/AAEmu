using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCAbilityExpChangedPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly byte _ability;
        private readonly int _exp;
        private readonly bool _isApplyAll;
        
        public SCAbilityExpChangedPacket(uint objId, AbilityType ability, int exp, bool isApplyAll = false) : base(SCOffsets.SCAbilityExpChangedPacket, 5)
        {
            _objId = objId;
            _ability = (byte) ability;
            _exp = exp;
            _isApplyAll = isApplyAll;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write(_ability);
            stream.Write(_exp);
            stream.Write(_isApplyAll);
            return stream;
        }
    }
}
