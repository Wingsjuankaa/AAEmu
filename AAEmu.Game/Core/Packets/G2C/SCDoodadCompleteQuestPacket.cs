using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Opens the native AA8 quest-completion directing UI for a doodad.
    /// AA8 x2game opcode 0x0AD serializes the doodad object id as BC followed
    /// by the UInt32 quest context id.
    /// </summary>
    public class SCDoodadCompleteQuestPacket : GamePacket
    {
        private readonly uint _doodadObjId;
        private readonly uint _questContextId;

        public SCDoodadCompleteQuestPacket(uint doodadObjId, uint questContextId)
            : base(SCOffsets.SCDoodadCompleteQuestPacket, 5)
        {
            _doodadObjId = doodadObjId;
            _questContextId = questContextId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_doodadObjId);
            stream.Write(_questContextId);
            return stream;
        }
    }
}
