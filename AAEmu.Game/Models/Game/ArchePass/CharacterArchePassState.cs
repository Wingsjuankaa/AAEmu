namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>Character-owned ArchePass state serialized by the r575 32-byte native record.</summary>
public sealed class CharacterArchePassState
{
    public int Type { get; init; }
    public long Point { get; set; }
    public ArchePassStatus Status { get; set; }
    public bool Premium { get; set; }
    public int LastRewardTier { get; set; }
    public int LastPremiumRewardTier { get; set; }
}
