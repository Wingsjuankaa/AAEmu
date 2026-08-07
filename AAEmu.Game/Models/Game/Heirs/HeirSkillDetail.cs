using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Models.Game.Heirs
{
    public sealed class HeirSkillDetail
    {
        public uint Id { get; set; }
        public uint HeirSkillId { get; set; }
        public uint SkillId { get; set; }
        public int Pos { get; set; }
        public SkillActiveType SkillActiveTypeId { get; set; }
        public string Desc { get; set; }
        public uint ActiveItemId { get; set; }
    }

    public enum HeirSkillResetKind : uint
    {
        All = 1,
        Ability = 2,
        Successor = 3
    }
}
