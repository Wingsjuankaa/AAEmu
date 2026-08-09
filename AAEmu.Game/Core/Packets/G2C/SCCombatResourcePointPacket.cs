using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>AA8 r558734: bc, resource id, point(int64), update time(uint32).</summary>
    public class SCCombatResourcePointPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly int _resourceId;
        private readonly ulong _precisePoint;
        private readonly uint _updateTime;

        public SCCombatResourcePointPacket(uint objId, int resourceId, long point, uint updateTime)
            : base(SCOffsets.SCCombatResourcePointPacket, 5)
        {
            _objId = objId;
            _resourceId = resourceId;
            _precisePoint = (ulong)System.Math.Max(0L, point) * 100UL;
            _updateTime = updateTime;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write(_resourceId);
            stream.Write(_precisePoint);
            stream.Write(_updateTime);
            return stream;
        }
    }
}
