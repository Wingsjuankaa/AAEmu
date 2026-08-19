using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>Server-authoritative weighted resolver for one Migration Scaling item.</summary>
public static class BlessUthstinCalculator
{
    public static BlessUthstinRoll Resolve(
        ItemBlessUthstinDefinition definition,
        IReadOnlyList<int> appliedStats,
        IReadOnlyList<int> defaultStats,
        int maximumPositiveStats,
        Random random)
    {
        if (definition is null || random is null ||
            appliedStats?.Count != ItemBlessUthstinDefinition.StatCount ||
            defaultStats?.Count != ItemBlessUthstinDefinition.StatCount ||
            definition.RiseWeights?.Length != ItemBlessUthstinDefinition.StatCount ||
            definition.DropWeights?.Length != ItemBlessUthstinDefinition.StatCount ||
            definition.RiseCount <= 0 || definition.DropCount <= 0 || maximumPositiveStats < 0)
            return null;

        var candidates = BuildCandidates(definition, appliedStats, defaultStats, maximumPositiveStats);
        var totalWeight = candidates.Sum(candidate => candidate.Weight);
        if (totalWeight <= 0)
            return null;

        var selected = random.NextInt64(totalWeight);
        foreach (var candidate in candidates)
        {
            if (selected < candidate.Weight)
                return new BlessUthstinRoll(
                    definition.ItemId,
                    definition.FunctionId,
                    (BlessUthstinStat)candidate.Increase,
                    (BlessUthstinStat)candidate.Decrease,
                    definition.RiseCount,
                    definition.DropCount,
                    0);
            selected -= candidate.Weight;
        }

        throw new InvalidOperationException("A valid Uthstin weighted roll was not selected.");
    }

    internal static IReadOnlyList<(int Increase, int Decrease, long Weight)> BuildCandidates(
        ItemBlessUthstinDefinition definition,
        IReadOnlyList<int> appliedStats,
        IReadOnlyList<int> defaultStats,
        int maximumPositiveStats)
    {
        var result = new List<(int Increase, int Decrease, long Weight)>();
        for (var increase = 0; increase < ItemBlessUthstinDefinition.StatCount; increase++)
        {
            if (definition.RiseWeights[increase] <= 0)
                continue;

            for (var decrease = 0; decrease < ItemBlessUthstinDefinition.StatCount; decrease++)
            {
                if (increase == decrease || definition.DropWeights[decrease] <= 0 ||
                    defaultStats[decrease] + appliedStats[decrease] < definition.DropCount)
                    continue;

                var changed = appliedStats.ToArray();
                changed[increase] += definition.RiseCount;
                changed[decrease] -= definition.DropCount;
                if (changed.Where(value => value > 0).Sum() > maximumPositiveStats)
                    continue;

                var weight = checked((long)definition.RiseWeights[increase] *
                                     definition.DropWeights[decrease]);
                if (weight > 0)
                    result.Add((increase, decrease, weight));
            }
        }

        return result;
    }
}
