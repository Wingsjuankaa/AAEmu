namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>Pure AA10 item-smelting outcome resolver.</summary>
public static class ItemSmeltingCalculator
{
    public const int ProbabilityBase = 10_000_000;

    public static ItemSmeltingOutcome Resolve(ItemSmeltingDefinition definition, int roll)
    {
        ArgumentNullException.ThrowIfNull(definition);
        if (definition.Probability is null || definition.Outputs.Count != 3)
            throw new ArgumentException("Smelting definition must have one probability row and three outputs.",
                nameof(definition));
        if (roll is < 0 or >= ProbabilityBase)
            throw new ArgumentOutOfRangeException(nameof(roll));

        var probability = definition.Probability;
        if (roll < probability.GreatSuccess)
            return new ItemSmeltingOutcome(ItemSmeltingResult.GreatSuccess, definition.Outputs[0]);
        if (roll < probability.GreatSuccess + probability.Success)
            return new ItemSmeltingOutcome(ItemSmeltingResult.Success, definition.Outputs[1]);
        return new ItemSmeltingOutcome(ItemSmeltingResult.Failure, definition.Outputs[2]);
    }
}
