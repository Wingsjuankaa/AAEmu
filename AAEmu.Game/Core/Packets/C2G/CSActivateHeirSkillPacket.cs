using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G
{
    /// <summary>Exact AA8 activation request: i32 heir, i32 successor, u8 isChange.</summary>
    public sealed class CSActivateHeirSkillPacket : GamePacket
    {
        public CSActivateHeirSkillPacket() : base(CSOffsets.CSActivateHeirSkillPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var heirSkillId = stream.ReadInt32();
            var successorSkillId = stream.ReadInt32();
            var isChange = stream.ReadBoolean();
            if (heirSkillId <= 0 || successorSkillId <= 0 || Connection.ActiveChar == null)
                return;
            Connection.ActiveChar.HeirSkills?.TryActivate(
                checked((uint)heirSkillId), checked((uint)successorSkillId), isChange);
        }
    }
}
