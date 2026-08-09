namespace AAEmu.Game.Models.Game.Skills.Templates
{
    public sealed class SkillHitCooldownReduction
    {
        public uint Id { get; set; }
        public uint SourceSkillId { get; set; }
        public uint TargetSkillId { get; set; }
        public uint TargetSkillTagId { get; set; }
        public int FlatMilliseconds { get; set; }
        public int Percent { get; set; }
        public bool PerDistinctTarget { get; set; }
    }
}
