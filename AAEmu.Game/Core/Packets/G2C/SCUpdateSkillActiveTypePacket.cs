using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public sealed class SCUpdateSkillActiveTypePacket : GamePacket
    {
        private readonly SkillActiveTypeEntry _entry;

        public SCUpdateSkillActiveTypePacket(SkillActiveTypeEntry entry)
            : base(SCOffsets.SCUpdateSkillActiveTypePacket, 5)
        {
            _entry = entry;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_entry.HeirSkillType);
            stream.Write(_entry.SkillType);
            stream.Write(_entry.ActiveType);
            return stream;
        }
    }
}
