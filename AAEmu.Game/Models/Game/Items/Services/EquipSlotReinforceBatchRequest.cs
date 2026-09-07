using System.Globalization;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>Custom UI quote. Quantities refer to real r575 recipe executions;
/// the server derives every item, price and experience value from its catalog.</summary>
public sealed record EquipSlotReinforceBatchRecipe(uint Material, int Count);

public sealed record EquipSlotReinforceBatchRequest(uint RequestId, byte Slot, sbyte Level, int Experience,
    int GainExperience, long Cost, IReadOnlyList<EquipSlotReinforceBatchRecipe> Recipes)
{
    public const uint SkillId = 38363;
    public const int MaxPayloadLength = 233;

    // Bounded ASCII quote transported in native channel-name fragments.
    public static EquipSlotReinforceBatchRequest Parse(string text)
    {
        if (string.IsNullOrEmpty(text) || text.Length > MaxPayloadLength) return null;
        var parts = text.Split('/');
        if (parts.Length is < 2 or > 9) return null;
        var header = parts[0].Split(',');
        if (header.Length != 6 || !uint.TryParse(header[0], NumberStyles.None, CultureInfo.InvariantCulture, out var requestId) || requestId == 0 ||
            !byte.TryParse(header[1], NumberStyles.None, CultureInfo.InvariantCulture, out var slot) ||
            !sbyte.TryParse(header[2], NumberStyles.None, CultureInfo.InvariantCulture, out var level) ||
            !int.TryParse(header[3], NumberStyles.None, CultureInfo.InvariantCulture, out var exp) ||
            !int.TryParse(header[4], NumberStyles.None, CultureInfo.InvariantCulture, out var gain) ||
            !long.TryParse(header[5], NumberStyles.None, CultureInfo.InvariantCulture, out var gold) ||
            level < 1 || exp < 0 || gain <= 0 || gold < 0) return null;
        var recipes = new List<EquipSlotReinforceBatchRecipe>();
        foreach (var part in parts.Skip(1))
        {
            var fields = part.Split(':');
            if (fields.Length != 2 || !uint.TryParse(fields[0], NumberStyles.None, CultureInfo.InvariantCulture, out var id) ||
                !int.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out var count) ||
                id == 0 || count is < 1 or > 100 || recipes.Any(r => r.Material == id)) return null;
            recipes.Add(new(id, count));
        }
        return new(requestId, slot, level, exp, gain, gold, recipes.AsReadOnly());
    }

    public EquipSlotReinforcePlan CreatePlan(EquipSlotReinforceGameData data, EquipSlotReinforceState state, bool useAaPoint)
    {
        if (RequestId == 0 || Experience < 0 || Recipes is null || Recipes.Count is < 1 or > 8 ||
            Recipes.Any(r => r is null) || Recipes.Sum(r => (long)r.Count) > 100 ||
            !data.Levels.TryGetValue((Slot, Level), out var level) || level.RequiredExperience <= 0 ||
            state.Get(Slot) != new EquipSlotReinforceProgress(Level, Experience) || Experience >= level.RequiredExperience)
            return null;
        long gain = 0, gold = 0;
        var materials = new Dictionary<uint, long>();
        var seen = new HashSet<uint>();
        var smallest = int.MaxValue;
        foreach (var recipe in Recipes)
        {
            if (!seen.Add(recipe.Material) || recipe.Count is < 1 or > 100 ||
                !data.Materials.TryGetValue(recipe.Material, out var row) || row.Slot != Slot || row.Level != Level ||
                row.Experience <= 0 || row.Cost < 0 || row.Currency != 0 ||
                !data.MaterialSets.TryGetValue(row.MaterialSet, out var items) || items.Count == 0) return null;
            gain += (long)row.Experience * recipe.Count;
            gold += (long)row.Cost * recipe.Count;
            smallest = Math.Min(smallest, row.Experience);
            foreach (var (item, count) in items)
            {
                if (item == 0 || count <= 0) return null;
                materials[item] = materials.GetValueOrDefault(item) + (long)count * recipe.Count;
            }
        }
        var needed = level.RequiredExperience - Experience;
        // Never accept extra whole recipe executions after reaching the target.
        if (gain != GainExperience || gold != Cost || gain < needed || gain - needed >= smallest ||
            materials.Count == 0 || materials.Values.Any(n => n > int.MaxValue)) return null;
        return new(state.With(Slot, new(Level, level.RequiredExperience)), Slot,
            materials.OrderBy(r => r.Key).Select(r => (r.Key, (int)r.Value)).ToArray(), gold, useAaPoint);
    }
}
