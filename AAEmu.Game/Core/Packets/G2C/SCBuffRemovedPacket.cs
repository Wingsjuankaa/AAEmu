    using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCBuffRemovedPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly uint _index;

        public SCBuffRemovedPacket(uint objId, uint index)
            : base(SCOffsets.SCBuffRemovedPacket, 5)
        {
            _objId = objId;
            _index = index;
        }

        public override PacketStream Write(PacketStream stream)
        {
            // AA8 SCBuffRemoved 0x023:
            // x64 factory FUN_393362a0 -> serializer FUN_399ab070
            // x86 factory FUN_393266f0 -> serializer FUN_39b81990
            stream.WriteBc(_objId);
            stream.Write(_index);
            return stream;
        }

        public override string Verbose()
        {
            return $" - owner={_objId}, index={_index}";
        }
    }
}
