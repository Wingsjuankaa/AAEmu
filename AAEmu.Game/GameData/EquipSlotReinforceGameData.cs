using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Items;
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
        LoadWindowProjection(connection);
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

    private readonly Dictionary<byte, List<EquipSlotReinforceStep>> _ladders = [];
    private readonly Dictionary<byte, EquipSlotReinforceAttribute> _attributeBySlot = [];
    private readonly Dictionary<(byte SlotTypeId, byte Level), List<AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial>> _materials = [];

    /// <summary>Every material row by its own id, since that is what the artifact window sends.</summary>
    private readonly Dictionary<uint, AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial> _materialsById = [];
    private readonly Dictionary<uint, EquipSlotReinforceLevelEffect> _levelEffectsById = [];
    private readonly Dictionary<uint, EquipSlotReinforceUnitModifier> _unitModifiersById = [];
    private readonly List<EquipSlotReinforceLevelEffect> _levelEffects = [];
    private readonly List<EquipSlotReinforceSetEffect> _setEffects = [];
    private readonly List<EquipSlotReinforceBundleEffect> _bundleEffects = [];

    private void LoadWindowProjection(SqliteConnection connection)
    {
        _ladders.Clear();
        _attributeBySlot.Clear();
        _materials.Clear();
        _materialsById.Clear();
        _levelEffectsById.Clear();
        _unitModifiersById.Clear();
        _levelEffects.Clear();
        _setEffects.Clear();
        _bundleEffects.Clear();

        LoadSteps(connection);
        LoadMaterials(connection);
        LoadLevelEffects(connection);
        LoadUnitModifiers(connection);
        LoadSetEffects(connection);
        LoadBundleEffects(connection);
    }



    private void LoadSteps(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT id, slot_type_id, level, need_exp, reinforce_attribute_id, gain_item_level, " +
            "level_up_item_id, level_up_item_count FROM equip_slot_reinforces";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            var step = new EquipSlotReinforceStep
            {
                Id = reader.GetUInt32("id"),
                SlotTypeId = reader.GetByte("slot_type_id"),
                Level = reader.GetByte("level"),
                NeedExp = reader.GetInt32("need_exp"),
                Attribute = (EquipSlotReinforceAttribute)reader.GetByte("reinforce_attribute_id"),
                GainItemLevel = reader.GetFloat("gain_item_level"),
                LevelUpItemId = reader.GetUInt32("level_up_item_id"),
                LevelUpItemCount = reader.GetInt32("level_up_item_count")
            };

            if (!_ladders.TryGetValue(step.SlotTypeId, out var ladder))
            {
                ladder = [];
                _ladders[step.SlotTypeId] = ladder;
            }

            ladder.Add(step);

            // A slot's ladder belongs to one attribute; the totals that gate the set and bundle
            // effects are sums over the slots of an attribute.
            if (!_attributeBySlot.ContainsKey(step.SlotTypeId))
                _attributeBySlot[step.SlotTypeId] = step.Attribute;
        }

        foreach (var ladder in _ladders.Values)
            ladder.Sort((left, right) => left.Level.CompareTo(right.Level));
    }

    private void LoadMaterials(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT id, name, require_level, gain_exp, currency_id, currency_value, " +
            "need_material_item_set_id, slot_type_id FROM equip_slot_reinforce_materials";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            var material = new AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial
            {
                Id = reader.GetUInt32("id"),
                Name = reader.GetString("name", string.Empty),
                RequireLevel = reader.GetByte("require_level"),
                GainExp = reader.GetInt32("gain_exp"),
                CurrencyId = reader.GetUInt32("currency_id"),
                CurrencyValue = reader.GetInt32("currency_value"),
                NeedMaterialItemSetId = reader.GetUInt32("need_material_item_set_id"),
                SlotTypeId = reader.GetByte("slot_type_id")
            };

            var key = (material.SlotTypeId, material.RequireLevel);
            if (!_materials.TryGetValue(key, out var list))
            {
                list = [];
                _materials[key] = list;
            }

            list.Add(material);

            // The artifact window names the material a player picked by its row id, and the row carries the
            // slot it belongs to, so this is what tells the server which slot a feed is for.
            _materialsById[material.Id] = material;
        }
    }

    /// <summary>
    /// A <c>equip_slot_reinforce_materials</c> row by its id, or null. The row knows which slot it feeds
    /// (<see cref="AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial.SlotTypeId"/>), which is how a window that sends only a material
    /// still lands on the right piece.
    /// </summary>
    public AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial GetMaterialById(uint materialId)
    {
        return _materialsById.GetValueOrDefault(materialId);
    }

    private void LoadLevelEffects(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, slot_type_id, trigger_level FROM equip_slot_reinforce_level_effects";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            var effect = new EquipSlotReinforceLevelEffect
            {
                Id = reader.GetUInt32("id"),
                SlotTypeId = reader.GetByte("slot_type_id"),
                TriggerLevel = reader.GetByte("trigger_level")
            };

            _levelEffectsById[effect.Id] = effect;
            _levelEffects.Add(effect);
        }
    }

    /// <summary>One <c>equip_slot_reinforce_level_effects</c> row by its id — a slot's tier.</summary>
    public EquipSlotReinforceLevelEffect GetLevelEffectById(uint levelEffectId)
    {
        return _levelEffectsById.GetValueOrDefault(levelEffectId);
    }

    /// <summary>
    /// One <c>equip_slot_reinforce_unit_modifiers</c> row by its id. A character stores the artifact effect it
    /// rolled as this id, so this is how the stored choice turns back into an attribute, a modifier type and
    /// a value.
    /// </summary>
    public EquipSlotReinforceUnitModifier GetUnitModifierById(uint unitModifierId)
    {
        return _unitModifiersById.GetValueOrDefault(unitModifierId);
    }

    private void LoadUnitModifiers(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT id, equip_slot_reinforce_level_effect_id, unit_attribute_id, " +
            "unit_modifier_type_id, value, weight FROM equip_slot_reinforce_unit_modifiers";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            var modifier = new EquipSlotReinforceUnitModifier
            {
                Id = reader.GetUInt32("id"),
                LevelEffectId = reader.GetUInt32("equip_slot_reinforce_level_effect_id"),
                UnitAttributeId = reader.GetUInt32("unit_attribute_id"),
                UnitModifierTypeId = reader.GetUInt32("unit_modifier_type_id"),
                Value = reader.GetInt32("value"),
                Weight = reader.GetInt32("weight")
            };

            _unitModifiersById[modifier.Id] = modifier;

            if (_levelEffectsById.TryGetValue(modifier.LevelEffectId, out var effect))
                effect.Modifiers.Add(modifier);
        }
    }

    private void LoadSetEffects(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT id, reinforce_attribute_id, require_reinforce_level, level, desc " +
            "FROM equip_slot_reinforce_set_effects";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            _setEffects.Add(new EquipSlotReinforceSetEffect
            {
                Id = reader.GetUInt32("id"),
                Attribute = (EquipSlotReinforceAttribute)reader.GetByte("reinforce_attribute_id"),
                RequireReinforceLevel = reader.GetByte("require_reinforce_level"),
                Level = reader.GetByte("level"),
                Desc = reader.GetString("desc", string.Empty)
            });
        }
    }

    private void LoadBundleEffects(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT id, bundle_effect_level, require_offense_level, require_defense_level, " +
            "require_support_level, desc FROM equip_slot_reinforce_bundle_effects";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);

        while (reader.Read())
        {
            _bundleEffects.Add(new EquipSlotReinforceBundleEffect
            {
                Id = reader.GetUInt32("id"),
                BundleEffectLevel = reader.GetByte("bundle_effect_level"),
                RequireOffenseLevel = reader.GetByte("require_offense_level"),
                RequireDefenseLevel = reader.GetByte("require_defense_level"),
                RequireSupportLevel = reader.GetByte("require_support_level"),
                Desc = reader.GetString("desc", string.Empty)
            });
        }
    }

    /// <summary>Every slot type that has a ladder, which is the set the client is told about.</summary>
    public IReadOnlyCollection<byte> SlotTypeIds => _ladders.Keys;

    public IReadOnlyList<EquipSlotReinforceStep> Ladder(byte slotTypeId)
    {
        return _ladders.TryGetValue(slotTypeId, out var ladder) ? ladder : [];
    }

    public EquipSlotReinforceStep Step(byte slotTypeId, byte level)
    {
        if (!_ladders.TryGetValue(slotTypeId, out var ladder))
            return null;

        foreach (var step in ladder)
        {
            if (step.Level == level)
                return step;
        }

        return null;
    }

    public EquipSlotReinforceAttribute? AttributeOf(byte slotTypeId)
    {
        return _attributeBySlot.TryGetValue(slotTypeId, out var attribute) ? attribute : null;
    }

    public IReadOnlyList<AAEmu.Game.Models.Game.Items.EquipSlotReinforceMaterial> MaterialsFor(byte slotTypeId, byte level)
    {
        return _materials.TryGetValue((slotTypeId, level), out var list) ? list : [];
    }

    public IReadOnlyList<EquipSlotReinforceLevelEffect> LevelEffects => _levelEffects;

    public IReadOnlyList<EquipSlotReinforceSetEffect> SetEffects => _setEffects;

    public IReadOnlyList<EquipSlotReinforceBundleEffect> BundleEffects => _bundleEffects;
}
