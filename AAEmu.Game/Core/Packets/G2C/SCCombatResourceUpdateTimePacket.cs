using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCCombatResourceUpdateTimePacket : GamePacket
    {
        private readonly uint _objId;
        private readonly int _resourceType;
        private readonly bool _showUpdateTime;

        public SCCombatResourceUpdateTimePacket(uint objId, int resourceType, bool showUpdateTime)
            : base(SCOffsets.SCCombatResourceUpdateTimePacket, 5)
        {
            _objId = objId;
            _resourceType = resourceType;
            _showUpdateTime = showUpdateTime;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write(_resourceType);
            stream.Write(_showUpdateTime);
            return stream;
        }
    }
}
