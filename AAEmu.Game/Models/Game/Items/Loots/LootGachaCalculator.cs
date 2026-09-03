using AAEmu.Game.GameData;

namespace AAEmu.Game.Models.Game.Items.Loots;

/// <summary>Pure AA10 Loot Gacha advanced-pack eligibility and pity selection.</summary>
public static class LootGachaCalculator
{
    public const int ProbabilityScale = 10_000_000;

    public static LootGachaAdvancedDefinition SelectAdvanced(
        IReadOnlyCollection<LootGachaAdvancedDefinition> definitions,
        uint currentRound,
        IReadOnlyDictionary<uint, uint> lastRounds,
        Random random)
    {
        ArgumentNullException.ThrowIfNull(random);
        if (definitions is null || currentRound == 0)
            return null;

        foreach (var definition in definitions.OrderBy(row => row.Priority).ThenBy(row => row.Id))
        {
            var lastRound = lastRounds?.GetValueOrDefault(definition.Id) ?? 0;
            var elapsed = currentRound >= lastRound ? currentRound - lastRound : 0;
            if (elapsed < definition.AddRound)
                continue;

            var pity = definition.GiveTerm > 0 && elapsed >= definition.GiveTerm;
            var chance = definition.Rate > 0 &&
                         random.Next(ProbabilityScale) < Math.Min(definition.Rate, ProbabilityScale);
            if (pity || chance)
                return definition;
        }

        return null;
    }
}
