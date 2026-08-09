using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCBuffUpdatedPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly Buff _buff;
        private readonly byte _reason;

        public SCBuffUpdatedPacket(uint objId, Buff buff, byte reason = 0)
            : base(SCOffsets.SCBuffUpdatedPacket, 5)
        {
            _objId = objId;
            _buff = buff;
            _reason = reason;
        }

        public override PacketStream Write(PacketStream stream)
        {
            // AA8 x2game.dll FUN_399aa9a0, opcode 0x1DE.
            stream.WriteBc(_objId);
            stream.Write(_buff.Index);
            stream.Write(_buff.Stack);
            stream.Write(_buff.Charge);
            stream.Write(_buff.GetTimeElapsed());
            stream.Write(_reason);
            return stream;
        }
    }
}
