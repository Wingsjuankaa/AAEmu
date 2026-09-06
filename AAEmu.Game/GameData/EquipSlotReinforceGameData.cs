using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.GameData;

public sealed record EquipSlotReinforceLevel(byte Slot, sbyte Level, int RequiredExperience,
    int Attribute, double GainItemLevel, uint LevelUpItem, int LevelUpCount);
public sealed record EquipSlotReinforceMaterial(uint Id, byte Slot, int Level, int Experience,
    int Currency, int Cost, uint MaterialSet);
public sealed record EquipSlotReinforceMilestone(uint Id, byte Slot, sbyte Level);
public sealed record EquipSlotReinforceModifier(uint Id, uint Milestone, BonusTemplate Bonus, int Weight);
public sealed record EquipSlotReinforceBundle(uint Id, int Offense, int Defense, int Support,
    IReadOnlyList<BonusTemplate> Bonuses);

[GameData]
public sealed class EquipSlotReinforceGameData : Singleton<EquipSlotReinforceGameData>, IGameDataLoader
{
    public Dictionary<(byte Slot, sbyte Level), EquipSlotReinforceLevel> Levels { get; } = [];
    public Dictionary<uint, EquipSlotReinforceMaterial> Materials { get; } = [];
    public Dictionary<uint, EquipSlotReinforceMilestone> Milestones { get; } = [];
    public Dictionary<uint, EquipSlotReinforceModifier> Modifiers { get; } = [];
    public Dictionary<uint, List<(uint Item, int Count)>> MaterialSets { get; } = [];
    public List<EquipSlotReinforceBundle> Bundles { get; } = [];
    public int MinimumLevel { get; private set; }
    public uint RerollItem { get; private set; }
    public bool UseItemLevelFormula { get; private set; }
    public bool UseBundles { get; private set; }
    public int IgnoredModifierCount { get; private set; }

    public void Load(SqliteConnection connection)
    {
        Levels.Clear(); Materials.Clear(); Milestones.Clear(); Modifiers.Clear();
        MaterialSets.Clear(); Bundles.Clear(); IgnoredModifierCount = 0;
        Read(connection, "SELECT * FROM equip_slot_reinforces", r =>
        {
            var row = new EquipSlotReinforceLevel((byte)r.GetInt32("slot_type_id"),
                (sbyte)r.GetInt32("level"), r.GetInt32("need_exp"), r.GetInt32("reinforce_attribute_id"),
                r.GetDouble("gain_item_level"), r.GetUInt32("level_up_item_id"), r.GetInt32("level_up_item_count"));
            Levels.Add((row.Slot, row.Level), row);
        });
        Read(connection, "SELECT * FROM equip_slot_reinforce_materials", r =>
        {
            var row = new EquipSlotReinforceMaterial(r.GetUInt32("id"), (byte)r.GetInt32("slot_type_id"),
                r.GetInt32("require_level"), r.GetInt32("gain_exp"), r.GetInt32("currency_id"),
                r.GetInt32("currency_value"), r.GetUInt32("need_material_item_set_id"));
            Materials.Add(row.Id, row);
        });
        Read(connection, "SELECT * FROM item_set_items WHERE item_set_id IN " +
            "(SELECT need_material_item_set_id FROM equip_slot_reinforce_materials)", r =>
        {
            var id = r.GetUInt32("item_set_id");
            if (!MaterialSets.TryGetValue(id, out var items)) MaterialSets[id] = items = [];
            items.Add((r.GetUInt32("item_id"), r.GetInt32("count")));
        });
        Read(connection, "SELECT * FROM equip_slot_reinforce_level_effects", r =>
        {
            var id = r.GetUInt32("id");
            Milestones.Add(id, new(id, (byte)r.GetInt32("slot_type_id"), (sbyte)r.GetInt32("trigger_level")));
        });
        Read(connection, "SELECT * FROM equip_slot_reinforce_unit_modifiers ORDER BY id", r =>
        {
            var milestone = r.GetUInt32("equip_slot_reinforce_level_effect_id");
            if (!Milestones.ContainsKey(milestone)) { IgnoredModifierCount++; return; }
            var id = r.GetUInt32("id");
            Modifiers.Add(id, new(id, milestone, new BonusTemplate
            {
                Attribute = (UnitAttribute)r.GetInt32("unit_attribute_id"),
                ModifierType = (UnitModifierType)r.GetInt32("unit_modifier_type_id"),
                Value = r.GetInt64("value")
            }, r.GetInt32("weight")));
        });
        var bonuses = new Dictionary<uint, List<BonusTemplate>>();
        Read(connection, "SELECT * FROM unit_modifiers WHERE owner_type='EquipSlotReinforceBundleEffect' AND enable='t'", r =>
        {
            var id = r.GetUInt32("owner_id");
            if (!bonuses.TryGetValue(id, out var values)) bonuses[id] = values = [];
            values.Add(new BonusTemplate
            {
                Attribute = (UnitAttribute)r.GetInt32("unit_attribute_id"),
                ModifierType = (UnitModifierType)r.GetInt32("unit_modifier_type_id"),
                Value = r.GetInt64("value")
            });
        });
        Read(connection, "SELECT * FROM equip_slot_reinforce_bundle_effects ORDER BY bundle_effect_level", r =>
        {
            var id = r.GetUInt32("id");
            Bundles.Add(new(id, r.GetInt32("require_offense_level"), r.GetInt32("require_defense_level"),
                r.GetInt32("require_support_level"), bonuses.GetValueOrDefault(id) ?? []));
        });
        var configs = new Dictionary<int, int>();
        Read(connection, "SELECT id,value FROM content_configs WHERE id IN (236,237,359,360)", r =>
            configs.Add(r.GetInt32("id"), r.GetInt32("value")));
        RerollItem = checked((uint)configs[236]); MinimumLevel = configs[237];
        UseItemLevelFormula = configs[359] > 0; UseBundles = configs[360] > 0;
    }

    public void PostLoad()
    {
        if (Levels.Count == 0 || MinimumLevel < 1 || RerollItem == 0 || !UseBundles)
            throw new InvalidDataException("Ipnya requires the r575 bundle catalogue and valid configuration.");
        foreach (var group in Levels.Values.GroupBy(r => r.Slot))
            if (!group.Select(r => (int)r.Level).Order().SequenceEqual(Enumerable.Range(1, group.Count())))
                throw new InvalidDataException($"Non-contiguous Ipnya levels for slot {group.Key}.");
        foreach (var row in Materials.Values.Where(r => Levels.ContainsKey((r.Slot, (sbyte)r.Level))))
            if (row.Cost < 0 || row.Experience <= 0 || row.Currency != 0 ||
                !MaterialSets.TryGetValue(row.MaterialSet, out var items) || items.Count == 0 ||
                items.Any(i => i.Item == 0 || i.Count <= 0))
                throw new InvalidDataException($"Invalid usable Ipnya material {row.Id}.");
        foreach (var milestone in Milestones.Values)
            if (!Modifiers.Values.Any(m => m.Milestone == milestone.Id && m.Weight > 0))
                throw new InvalidDataException($"Ipnya milestone {milestone.Id} has no weighted effects.");
        LogManager.GetCurrentClassLogger().Info(
            "Ipnya catalog: {0} levels, {1} materials, {2} milestones, {3} usable modifiers, {4} orphan modifiers excluded",
            Levels.Count, Materials.Count, Milestones.Count, Modifiers.Count, IgnoredModifierCount);
    }

    private static void Read(SqliteConnection connection, string sql, Action<SQLiteWrapperReader> action)
    {
        using var command = connection.CreateCommand(); command.CommandText = sql;
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read()) action(reader);
    }
}
