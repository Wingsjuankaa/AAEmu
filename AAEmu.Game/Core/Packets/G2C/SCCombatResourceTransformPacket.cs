using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCCombatResourceTransformPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly int _groupType;
        private readonly bool _transform;

        public SCCombatResourceTransformPacket(uint objId, int groupType, bool transform)
            : base(SCOffsets.SCCombatResourceTransformPacket, 5)
        {
            _objId = objId;
            _groupType = groupType;
            _transform = transform;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write(_groupType);
            stream.Write(_transform);
            return stream;
        }
    }
}
