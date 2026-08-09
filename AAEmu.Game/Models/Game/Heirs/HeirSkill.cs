using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Heirs
{
    public sealed class HeirSkill
    {
        public uint Id { get; set; }
        public uint SkillId { get; set; }
        public byte Step { get; set; }
        public bool Enable { get; set; }
        public IReadOnlyList<HeirSkillDetail> Successors { get; set; }
    }
}
