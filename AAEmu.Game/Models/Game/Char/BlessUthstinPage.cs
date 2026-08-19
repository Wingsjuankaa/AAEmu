namespace AAEmu.Game.Models.Game.Char;

public sealed class BlessUthstinPage
{
    public int[] Stats { get; } = new int[5];
    public int NormalApplyCount { get; set; }
    public int SpecialApplyCount { get; set; }

    public BlessUthstinPage Clone()
    {
        var clone = new BlessUthstinPage
        {
            NormalApplyCount = NormalApplyCount,
            SpecialApplyCount = SpecialApplyCount
        };
        Stats.CopyTo(clone.Stats, 0);
        return clone;
    }
}
