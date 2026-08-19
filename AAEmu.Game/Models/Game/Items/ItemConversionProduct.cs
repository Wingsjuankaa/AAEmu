namespace AAEmu.Game.Models.Game.Items;

public sealed class ItemConversionProduct
{
    public uint ProductPackId { get; init; }
    public uint OutputItemId { get; init; }
    public int Weight { get; init; }
    public int MinOutput { get; init; }
    public int MaxOutput { get; init; }
    public int GradeId { get; init; }
}

public sealed class ItemConversionProductPack
{
    public uint Id { get; init; }
    public int ChanceRate { get; init; }
    public List<ItemConversionProduct> Products { get; } = [];
}

public sealed class ItemConversionRoute
{
    public uint Id { get; init; }
    public string Name { get; init; }
    public int SetId { get; init; }
    public List<ItemConversionReagent> Reagents { get; } = [];
    public List<ItemConversionProductPack> ProductPacks { get; } = [];
}

public readonly record struct ItemConversionReward(uint ItemId, int Amount, int GradeId);

public sealed class ItemConversionResolution
{
    public bool IsValid { get; init; }
    public string FailureReason { get; init; }
    public ItemConversionRoute Route { get; init; }
    public IReadOnlyList<ItemConversionReward> Rewards { get; init; } = [];

    public static ItemConversionResolution Failure(string reason) => new()
    {
        FailureReason = reason
    };
}
