using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Models.Game.Items.Services;

public sealed record EquipSlotReinforcePlan(EquipSlotReinforceState State, byte Slot,
    IReadOnlyCollection<(uint Item, int Count)> Materials, long Cost, bool UseAaPoint,
    EquipSlotReinforceEffectKey? ChangedEffect = null, uint ModifierId = 0);

/// <summary>Plans without touching inventory, currency or the current immutable character state.</summary>
public static class EquipSlotReinforceCalculator
{
    public static EquipSlotReinforcePlan AddExperience(EquipSlotReinforceGameData data,
        EquipSlotReinforceState state, byte slot, uint materialId, bool useAaPoint)
    {
        var current = state.Get(slot);
        if (!data.Levels.TryGetValue((slot, current.Level), out var level) ||
            level.RequiredExperience <= 0 || current.Experience >= level.RequiredExperience ||
            !data.Materials.TryGetValue(materialId, out var material) ||
            material.Slot != slot || material.Level != current.Level || material.Experience <= 0 ||
            material.Cost < 0 || material.Currency != 0 ||
            !data.MaterialSets.TryGetValue(material.MaterialSet, out var requirements))
            return null;
        // The native add-EXP dialog explicitly confirms discarded overflow. Promotion is separate.
        var exp = (int)Math.Min(level.RequiredExperience, (long)current.Experience + material.Experience);
        return new(state.With(slot, current with { Experience = exp }), slot, requirements.ToArray(),
            material.Cost, useAaPoint);
    }

    public static EquipSlotReinforcePlan LevelUp(EquipSlotReinforceGameData data,
        EquipSlotReinforceState state, byte slot, Func<int, int> next)
    {
        var current = state.Get(slot);
        if (!data.Levels.TryGetValue((slot, current.Level), out var level) ||
            level.RequiredExperience <= 0 || current.Experience != level.RequiredExperience ||
            !data.Levels.ContainsKey((slot, (sbyte)(current.Level + 1))) ||
            level.LevelUpItem == 0 || level.LevelUpCount <= 0)
            return null;
        var newLevel = (sbyte)(current.Level + 1);
        var milestone = data.Milestones.Values.SingleOrDefault(m => m.Slot == slot && m.Level == newLevel);
        var modifier = milestone is null ? null : Roll(data, milestone.Id, next);
        if (milestone is not null && modifier is null) return null;
        EquipSlotReinforceEffectKey? key = milestone is null ? null : new(slot, newLevel);
        return new(state.With(slot, new(newLevel, 0), key, modifier?.Id ?? 0), slot,
            [(level.LevelUpItem, level.LevelUpCount)], 0, false, key, modifier?.Id ?? 0);
    }

    public static EquipSlotReinforcePlan ChangeEffect(EquipSlotReinforceGameData data,
        EquipSlotReinforceState state, byte slot, sbyte effectLevel, Func<int, int> next)
    {
        var current = state.Get(slot);
        var key = new EquipSlotReinforceEffectKey(slot, effectLevel);
        if (effectLevel > current.Level || !state.Effects.ContainsKey(key) || data.RerollItem == 0)
            return null;
        var milestone = data.Milestones.Values.SingleOrDefault(m => m.Slot == slot && m.Level == effectLevel);
        var modifier = milestone is null ? null : Roll(data, milestone.Id, next, state.Effects[key]);
        if (modifier is null) return null;
        return new(state.With(slot, current, key, modifier.Id), slot, [(data.RerollItem, 1)], 0, false,
            key, modifier.Id);
    }

    private static EquipSlotReinforceModifier Roll(EquipSlotReinforceGameData data, uint milestone,
        Func<int, int> next, uint excludeModifier = 0)
    {
        // Native ui_texts 9256: replacing an effect cannot reapply the existing effect.
        var options = data.Modifiers.Values.Where(m => m.Milestone == milestone && m.Weight > 0 && m.Id != excludeModifier)
            .OrderBy(m => m.Id).ToArray();
        var total = options.Sum(m => m.Weight);
        if (total <= 0) return null;
        var roll = next(total);
        if (roll < 0 || roll >= total) throw new ArgumentOutOfRangeException(nameof(next));
        foreach (var option in options)
        {
            if (roll < option.Weight) return option;
            roll -= option.Weight;
        }
        throw new InvalidOperationException("Ipnya weight table did not cover its roll.");
    }

    public static IReadOnlyList<Bonus> GetBonuses(EquipSlotReinforceGameData data, EquipSlotReinforceState state)
    {
        var result = new List<Bonus>();
        foreach (var (key, id) in state.Effects)
            if (key.Level <= state.Get(key.Slot).Level && data.Modifiers.TryGetValue(id, out var modifier))
                result.Add(new() { Template = modifier.Bonus, Value = modifier.Bonus.Value });
        var totals = data.Levels.Values.Where(l => l.Level == 1)
            .GroupBy(l => l.Attribute).ToDictionary(g => g.Key, g => g.Sum(l => (int)state.Get(l.Slot).Level));
        foreach (var bundle in data.Bundles)
            if (totals.GetValueOrDefault(1) >= bundle.Offense && totals.GetValueOrDefault(2) >= bundle.Defense &&
                totals.GetValueOrDefault(3) >= bundle.Support)
                result.AddRange(bundle.Bonuses.Select(b => new Bonus { Template = b, Value = b.Value }));
        return result;
    }
}
