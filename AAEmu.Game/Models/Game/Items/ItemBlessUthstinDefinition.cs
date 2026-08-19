namespace AAEmu.Game.Models.Game.Items;

/// <summary>
/// Exact r575 row from <c>item_bless_uthstins</c>. Stat order is
/// Strength, Dexterity, Stamina, Intelligence and Spirit.
/// </summary>
public sealed class ItemBlessUthstinDefinition
{
    public const int StatCount = 5;

    public uint ItemId { get; init; }
    public int FunctionId { get; init; }
    public int RiseCount { get; init; }
    public int DropCount { get; init; }
    public int[] RiseWeights { get; init; } = new int[StatCount];
    public int[] DropWeights { get; init; } = new int[StatCount];
}
