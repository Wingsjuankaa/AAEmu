using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>AA8 opcode 0x341: u32 kind, i32 successor, i8 ability.</summary>
    public sealed class SCResetHeirSkillPacket : GamePacket
    {
        private readonly uint _kind;
        private readonly int _successorSkillId;
        private readonly sbyte _ability;

        public SCResetHeirSkillPacket(uint kind, int successorSkillId, sbyte ability)
            : base(SCOffsets.SCResetHeirSkillPacket, 5)
        {
            _kind = kind;
            _successorSkillId = successorSkillId;
            _ability = ability;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_kind);
            stream.Write(_successorSkillId);
            stream.Write(_ability);
            return stream;
        }
    }
}
