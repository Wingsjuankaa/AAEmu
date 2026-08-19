namespace AAEmu.Game.Models.Game.Items;

/// <summary>
/// One native AA10 item-smelting recipe. The client selects it by id through skill-object type 20.
/// </summary>
public sealed class ItemSmeltingDefinition
{
    public uint Id { get; init; }
    public int ActabilityLimit { get; init; }
    public int Amount { get; init; }
    public int Gold { get; init; }
    public uint ItemSetId { get; init; }
    public uint ProbabilityId { get; init; }
    public uint ItemId { get; init; }
    public uint SkillId { get; init; }
    public ItemSmeltingProbability Probability { get; set; }

    /// <summary>
    /// Native insertion order: Great Success, Success, Failure. The client builds the same vector by
    /// scanning <c>item_smelting_items</c> in row-id order and attaching matching rows to this recipe.
    /// </summary>
    public List<ItemSmeltingOutput> Outputs { get; } = [];
}

public sealed class ItemSmeltingProbability
{
    public uint Id { get; init; }
    public int GreatSuccess { get; init; }
    public int Success { get; init; }
    public int Failure { get; init; }
}

public sealed class ItemSmeltingOutput
{
    public uint Id { get; init; }
    public int DisplayProbability { get; init; }
    public byte GradeId { get; init; }
    public uint SmeltingId { get; init; }
    public uint ItemId { get; init; }
}

/// <summary>Wire result values consumed by the r575 ITEM_SMELTING_RESULT handler.</summary>
public enum ItemSmeltingResult : sbyte
{
    Failure = 0,
    Success = 1,
    GreatSuccess = 2
}

public sealed record ItemSmeltingOutcome(ItemSmeltingResult Result, ItemSmeltingOutput Output);
