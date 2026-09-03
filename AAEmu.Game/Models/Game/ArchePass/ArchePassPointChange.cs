namespace AAEmu.Game.Models.Game.ArchePass;

public sealed record ArchePassPointChange(int Type, long PreviousPoint, long Point, int Tier)
{
    public int AppliedPoints => checked((int)(Point - PreviousPoint));
}
