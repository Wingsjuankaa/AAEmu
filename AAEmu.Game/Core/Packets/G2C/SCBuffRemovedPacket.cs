    using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCBuffRemovedPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly uint _index;
        private readonly byte _reason;

        public SCBuffRemovedPacket(uint objId, uint index, byte reason = 0)
            : base(SCOffsets.SCBuffRemovedPacket, 5)
        {
            _objId = objId;
            _index = index;
            _reason = reason;
        }

        public override PacketStream Write(PacketStream stream)
        {
            // AA8 x2game.dll FUN_399ad0f0 (x64) / FUN_39b83420 (x86).
            stream.WriteBc(_objId); // unitId
            stream.Write(_index);   // buffId (runtime index)
            stream.Write(_reason);
            return stream;
        }

        public override string Verbose()
        {
            return $" - owner={_objId}, index={_index}, reason={_reason}";
        }
    }
}
