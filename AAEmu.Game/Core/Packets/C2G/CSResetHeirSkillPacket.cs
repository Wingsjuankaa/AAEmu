using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Heirs;

namespace AAEmu.Game.Core.Packets.C2G
{
    /// <summary>Exact AA8 reset request: u32 kind, i8 ability, i32 successor.</summary>
    public sealed class CSResetHeirSkillPacket : GamePacket
    {
        public CSResetHeirSkillPacket() : base(CSOffsets.CSResetHeirSkillPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var kind = stream.ReadUInt32();
            var ability = stream.ReadSByte();
            var successorSkillId = stream.ReadInt32();
            if (!Enum.IsDefined(typeof(HeirSkillResetKind), kind) || Connection.ActiveChar == null)
                return;
            Connection.ActiveChar.HeirSkills?.TryReset(
                (HeirSkillResetKind)kind, ability, successorSkillId);
        }
    }
}
