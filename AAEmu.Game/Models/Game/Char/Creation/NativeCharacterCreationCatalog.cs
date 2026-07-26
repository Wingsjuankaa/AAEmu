using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;

namespace AAEmu.Game.Models.Game.Char.Creation
{
    /// <summary>
    /// Immutable, fully resolved AA8 character bootstrap. No identifier is allocated
    /// while this plan is being built.
    /// </summary>
    public sealed class CharacterBootstrapPlan
    {
        public uint CharacterTemplateId { get; }
        public Race Race { get; }
        public Gender Gender { get; }
        public uint ModelId { get; }
        public uint FactionId { get; }
        public uint ReturnDistrictId { get; }
        public uint ResurrectionDistrictId { get; }
        public byte InventorySlots { get; }
        public short BankSlots { get; }
        public AbilityType InitialAbility { get; }
        public WorldSpawnPosition Spawn { get; }
        public IReadOnlyList<NativeCreationItem> Equipment { get; }
        public IReadOnlyList<NativeCreationItem> Supplies { get; }
        public IReadOnlyList<uint> LearnedSkills { get; }
        public IReadOnlyList<uint> DefaultSkills { get; }
        public IReadOnlyList<ActionSlot> Actions { get; }

        internal CharacterBootstrapPlan(
            NativeCreationTemplate template,
            AbilityType initialAbility,
            IEnumerable<NativeCreationItem> equipment,
            IEnumerable<NativeCreationItem> supplies,
            IEnumerable<uint> learnedSkills,
            IEnumerable<uint> defaultSkills,
            IEnumerable<ActionSlot> actions)
        {
            CharacterTemplateId = template.Id;
            Race = (Race)template.Race;
            Gender = (Gender)template.Gender;
            ModelId = template.ModelId;
            FactionId = template.FactionId;
            ReturnDistrictId = template.ReturnDistrictId;
            ResurrectionDistrictId = template.ResurrectionDistrictId;
            InventorySlots = template.InventorySlots;
            BankSlots = template.BankSlots;
            InitialAbility = initialAbility;
            Spawn = template.Spawn.Clone();
            Equipment = new ReadOnlyCollection<NativeCreationItem>(equipment.ToList());
            Supplies = new ReadOnlyCollection<NativeCreationItem>(supplies.ToList());
            LearnedSkills = new ReadOnlyCollection<uint>(learnedSkills.ToList());
            DefaultSkills = new ReadOnlyCollection<uint>(defaultSkills.ToList());
            Actions = new ReadOnlyCollection<ActionSlot>(
                actions.Select(x => new ActionSlot { Type = x.Type, ActionId = x.ActionId }).ToList());
        }
    }

    public sealed class NativeCreationItem
    {
        public uint SourceRowId { get; }
        public uint TemplateId { get; }
        public int Amount { get; }
        public byte Grade { get; }
        public SlotType Container { get; }
        public int Slot { get; }

        public NativeCreationItem(
            uint sourceRowId,
            uint templateId,
            int amount,
            byte grade,
            SlotType container,
            int slot)
        {
            SourceRowId = sourceRowId;
            TemplateId = templateId;
            Amount = amount;
            Grade = grade;
            Container = container;
            Slot = slot;
        }
    }

    internal sealed class NativeCreationTemplate
    {
        public uint Id;
        public byte Race;
        public byte Gender;
        public uint ModelId;
        public uint FactionId;
        public uint ReturnDistrictId;
        public uint ResurrectionDistrictId;
        public byte InventorySlots;
        public short BankSlots;
        public WorldSpawnPosition Spawn;
        public List<uint> DefaultSkills = new List<uint>();
    }

    internal struct NativeCreationKey : IEquatable<NativeCreationKey>
    {
        public readonly byte Race;
        public readonly byte Gender;
        public readonly byte Ability;

        public NativeCreationKey(byte race, byte gender, byte ability)
        {
            Race = race;
            Gender = gender;
            Ability = ability;
        }

        public bool Equals(NativeCreationKey other)
        {
            return Race == other.Race && Gender == other.Gender && Ability == other.Ability;
        }

        public override bool Equals(object obj)
        {
            return obj is NativeCreationKey other && Equals(other);
        }

        public override int GetHashCode()
        {
            unchecked
            {
                return (Race * 397) ^ (Gender * 31) ^ Ability;
            }
        }
    }

    /// <summary>
    /// AA8-only creation catalogue. Derived tables are deliberately mandatory
    /// and retain their native or explicitly accepted server-derived provenance
    /// in the reconstruction manifest.
    /// </summary>
    public sealed class NativeCharacterCreationCatalog
    {
        public const byte NativeLevel = 1;
        public const int NativeIntroZoneSentinel = -1;
        public const byte NativeUnusedAbilitySentinel = (byte)AbilityType.None;

        private static readonly string[] RequiredDerivedTables =
        {
            "native_character_creation_spawns",
            "native_character_creation_inventory",
            "native_character_creation_supply_slots",
            "native_character_creation_action_slots"
        };

        private readonly Dictionary<NativeCreationKey, CharacterBootstrapPlan> _plans =
            new Dictionary<NativeCreationKey, CharacterBootstrapPlan>();
        private readonly Dictionary<uint, NativeCreationTemplate> _templatesById =
            new Dictionary<uint, NativeCreationTemplate>();
        private readonly Dictionary<int, HashSet<uint>> _bodyItemsByModelAndSlot =
            new Dictionary<int, HashSet<uint>>();

        public bool IsReady { get; private set; }
        public string FailureReason { get; private set; } = "catalogue not loaded";

        public static WorldSpawnPosition ResolveRuntimeSpawn(
            WorldSpawnPosition source,
            uint mainWorldId)
        {
            if (source == null)
                throw new ArgumentNullException(nameof(source));

            var resolved = source.Clone();
            resolved.WorldId = mainWorldId;
            return resolved;
        }

        public void Load(uint mainWorldId)
        {
            IsReady = false;
            FailureReason = string.Empty;
            _plans.Clear();
            _templatesById.Clear();
            _bodyItemsByModelAndSlot.Clear();

            try
            {
                using (var connection = SQLite.CreateConnection())
                {
                    var missing = RequiredDerivedTables
                        .Where(table => !TableExists(connection, table))
                        .ToArray();
                    if (missing.Length > 0)
                        throw new InvalidOperationException(
                            "AA8 bootstrap gate remains open; missing derived tables: " +
                            string.Join(", ", missing));

                    LoadTemplates(connection, mainWorldId);
                    LoadBodyCompatibility(connection);
                    LoadPlans(connection);
                }

                if (_templatesById.Count != 12)
                    throw new InvalidOperationException(
                        $"AA8 playable character matrix expected 12 race/gender templates, found {_templatesById.Count}");
                if (_plans.Count != 96)
                    throw new InvalidOperationException(
                        $"AA8 playable matrix expected 96 race/gender/ability plans, found {_plans.Count}");

                IsReady = true;
            }
            catch (Exception exception)
            {
                FailureReason = exception.Message;
                _plans.Clear();
                IsReady = false;
            }
        }

        public bool TryResolve(
            byte race,
            byte gender,
            uint[] body,
            byte[] abilities,
            byte level,
            int introZoneId,
            out CharacterBootstrapPlan plan,
            out string error)
        {
            plan = null;
            error = string.Empty;
            if (!IsReady)
            {
                error = FailureReason;
                return false;
            }
            if (body == null || body.Length != 7)
            {
                error = "AA8 creation requires exactly seven body item identifiers";
                return false;
            }
            if (abilities == null || abilities.Length != 3 ||
                abilities[0] == (byte)AbilityType.General ||
                abilities[0] == NativeUnusedAbilitySentinel ||
                abilities[1] != NativeUnusedAbilitySentinel ||
                abilities[2] != NativeUnusedAbilitySentinel)
            {
                error =
                    "AA8 creation requires one selected initial ability and " +
                    "two AbilityType.None (30) sentinels";
                return false;
            }
            if (level != NativeLevel || introZoneId != NativeIntroZoneSentinel)
            {
                error =
                    $"AA8 creation sentinels differ: level={level}, introZoneId={introZoneId}";
                return false;
            }

            var key = new NativeCreationKey(race, gender, abilities[0]);
            if (!_plans.TryGetValue(key, out plan))
            {
                error = $"unsupported AA8 race/gender/ability combination {race}/{gender}/{abilities[0]}";
                return false;
            }

            for (var index = 0; index < body.Length; index++)
            {
                var itemId = body[index];
                var compatibilityKey = checked((int)(plan.ModelId * 32 + (uint)index));
                _bodyItemsByModelAndSlot.TryGetValue(compatibilityKey, out var validItems);
                var validEmpty = itemId == 0 &&
                                 (validItems == null || validItems.Contains(0));
                var validConcrete = itemId != 0 &&
                                    validItems != null &&
                                    validItems.Contains(itemId);
                if (!validEmpty && !validConcrete)
                {
                    error =
                        $"body item {itemId} is not native for model {plan.ModelId}, slot {index + 19}";
                    plan = null;
                    return false;
                }
            }

            var equipmentWithBody = plan.Equipment.ToList();
            for (var index = 0; index < body.Length; index++)
            {
                if (body[index] == 0)
                    continue;
                equipmentWithBody.Add(new NativeCreationItem(
                    0,
                    body[index],
                    1,
                    0,
                    SlotType.Equipment,
                    index + (int)EquipmentItemSlot.Face));
            }

            var template = _templatesById[plan.CharacterTemplateId];
            try
            {
                ValidateReferencesAndSpace(
                    template,
                    equipmentWithBody,
                    plan.Supplies,
                    plan.LearnedSkills,
                    plan.Actions);
            }
            catch (Exception exception)
            {
                error = exception.Message;
                plan = null;
                return false;
            }
            plan = new CharacterBootstrapPlan(
                template,
                plan.InitialAbility,
                equipmentWithBody,
                plan.Supplies,
                plan.LearnedSkills,
                plan.DefaultSkills,
                plan.Actions);
            return true;
        }

        private static bool TableExists(SqliteConnection connection, string table)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=@name";
                var parameter = command.CreateParameter();
                parameter.ParameterName = "@name";
                parameter.Value = table;
                command.Parameters.Add(parameter);
                return Convert.ToInt32(command.ExecuteScalar()) == 1;
            }
        }

        private void LoadTemplates(
            SqliteConnection connection,
            uint mainWorldId)
        {
            const string sql =
                "SELECT c.id,c.char_race_id,c.char_gender_id,c.model_id,c.faction_id," +
                "c.starting_zone_id,c.default_return_district_id," +
                "c.default_resurrection_district_id,s.world_id,s.zone_id,s.x,s.y,s.z," +
                "s.roll,s.pitch,s.yaw,i.inventory_slots,i.bank_slots " +
                "FROM characters c " +
                "JOIN native_character_creation_spawns s ON s.character_id=c.id " +
                "JOIN native_character_creation_inventory i ON i.character_id=c.id " +
                "ORDER BY c.id";
            using (var command = connection.CreateCommand())
            {
                command.CommandText = sql;
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        var template = new NativeCreationTemplate
                        {
                            Id = reader.GetUInt32("id"),
                            Race = reader.GetByte("char_race_id"),
                            Gender = reader.GetByte("char_gender_id"),
                            ModelId = reader.GetUInt32("model_id"),
                            FactionId = reader.GetUInt32("faction_id"),
                            ReturnDistrictId = reader.GetUInt32("default_return_district_id"),
                            ResurrectionDistrictId =
                                reader.GetUInt32("default_resurrection_district_id"),
                            InventorySlots = reader.GetByte("inventory_slots"),
                            BankSlots = reader.GetInt16("bank_slots"),
                            Spawn = ResolveRuntimeSpawn(
                                new WorldSpawnPosition
                            {
                                WorldId = reader.GetUInt32("world_id"),
                                ZoneId = reader.GetUInt32("zone_id"),
                                X = reader.GetFloat("x"),
                                Y = reader.GetFloat("y"),
                                Z = reader.GetFloat("z"),
                                Roll = reader.GetFloat("roll"),
                                Pitch = reader.GetFloat("pitch"),
                                Yaw = reader.GetFloat("yaw")
                            },
                                mainWorldId)
                        };
                        if (template.Spawn.ZoneId != reader.GetUInt32("starting_zone_id"))
                            throw new InvalidOperationException(
                                $"spawn zone mismatch for AA8 character row {template.Id}");
                        if (!_templatesById.TryAdd(template.Id, template))
                            throw new InvalidOperationException(
                                $"duplicate AA8 character row {template.Id}");
                    }
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT cds.character_id,ds.skill_id " +
                    "FROM character_default_skills cds " +
                    "JOIN default_skills ds ON ds.id=cds.default_skill_id " +
                    "ORDER BY cds.character_id,cds.default_skill_id";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        var characterId = reader.GetUInt32("character_id");
                        if (!_templatesById.TryGetValue(characterId, out var template))
                            throw new InvalidOperationException(
                                $"default skill references missing character row {characterId}");
                        var skillId = reader.GetUInt32("skill_id");
                        if (SkillManager.Instance.GetSkillTemplate(skillId) == null)
                            throw new InvalidOperationException(
                                $"default skill references missing skill {skillId}");
                        template.DefaultSkills.Add(skillId);
                    }
                }
            }
        }

        private void LoadBodyCompatibility(SqliteConnection connection)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT model_id,item_id,slot_type_id FROM item_body_parts " +
                    "WHERE slot_type_id BETWEEN 23 AND 29 ORDER BY model_id,slot_type_id,item_id";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        var modelId = reader.GetUInt32("model_id");
                        var bodyIndex = reader.GetInt32("slot_type_id") - 23;
                        var itemId = reader.GetUInt32("item_id");
                        var key = checked((int)(modelId * 32 + (uint)bodyIndex));
                        if (!_bodyItemsByModelAndSlot.TryGetValue(key, out var items))
                        {
                            items = new HashSet<uint>();
                            _bodyItemsByModelAndSlot.Add(key, items);
                        }
                        items.Add(itemId);
                    }
                }
            }
        }

        private void LoadPlans(SqliteConnection connection)
        {
            var abilities = new Dictionary<byte, uint>();
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT ability_id,start_equip_pack_id FROM login_stage_abilities " +
                    "ORDER BY ability_id";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        var ability = reader.GetByte("ability_id");
                        if (!abilities.TryAdd(ability, reader.GetUInt32("start_equip_pack_id")))
                            throw new InvalidOperationException(
                                $"duplicate AA8 login-stage ability {ability}");
                    }
                }
            }
            if (abilities.Count != 8)
                throw new InvalidOperationException(
                    $"AA8 login stage expected 8 selectable abilities, found {abilities.Count}");

            foreach (var template in _templatesById.Values.OrderBy(x => x.Id))
            {
                foreach (var ability in abilities.OrderBy(x => x.Key))
                {
                    var equipment = ReadEquipment(connection, ability.Value);
                    var supplies = ReadSupplies(connection, ability.Key);
                    var selectedSkills = ReadSelectedSkills(connection, ability.Key);
                    var actions = ReadActions(connection, template.Id, ability.Key);
                    ValidateReferencesAndSpace(template, equipment, supplies, selectedSkills, actions);

                    var key = new NativeCreationKey(template.Race, template.Gender, ability.Key);
                    _plans.Add(
                        key,
                        new CharacterBootstrapPlan(
                            template,
                            (AbilityType)ability.Key,
                            equipment,
                            supplies,
                            selectedSkills,
                            template.DefaultSkills,
                            actions));
                }
            }
        }

        private static List<NativeCreationItem> ReadEquipment(
            SqliteConnection connection,
            uint equipPackId)
        {
            const string sql =
                "SELECT c.*,w.* FROM character_equip_packs p " +
                "JOIN equip_pack_cloths c ON c.id=p.newbie_cloth_pack_id " +
                "JOIN equip_pack_weapons w ON w.id=p.newbie_weapon_pack_id " +
                "WHERE p.id=@id";
            using (var command = connection.CreateCommand())
            {
                command.CommandText = sql;
                var parameter = command.CreateParameter();
                parameter.ParameterName = "@id";
                parameter.Value = equipPackId;
                command.Parameters.Add(parameter);
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    if (!reader.Read())
                        throw new InvalidOperationException(
                            $"AA8 equip pack {equipPackId} has no complete cloth/weapon relation");
                    var result = new List<NativeCreationItem>();
                    AddEquipment(result, reader, "headgear", EquipmentItemSlot.Head);
                    AddEquipment(result, reader, "necklace", EquipmentItemSlot.Neck);
                    AddEquipment(result, reader, "shirt", EquipmentItemSlot.Chest);
                    AddEquipment(result, reader, "belt", EquipmentItemSlot.Waist);
                    AddEquipment(result, reader, "pants", EquipmentItemSlot.Legs);
                    AddEquipment(result, reader, "glove", EquipmentItemSlot.Hands);
                    AddEquipment(result, reader, "shoes", EquipmentItemSlot.Feet);
                    AddEquipment(result, reader, "bracelet", EquipmentItemSlot.Arms);
                    AddEquipment(result, reader, "back", EquipmentItemSlot.Back);
                    AddEquipment(result, reader, "undershirt", EquipmentItemSlot.Undershirt);
                    AddEquipment(result, reader, "underpants", EquipmentItemSlot.Underpants);
                    AddEquipment(result, reader, "mainhand", EquipmentItemSlot.Mainhand);
                    AddEquipment(result, reader, "offhand", EquipmentItemSlot.Offhand);
                    AddEquipment(result, reader, "ranged", EquipmentItemSlot.Ranged);
                    AddEquipment(result, reader, "musical", EquipmentItemSlot.Musical);
                    AddEquipment(result, reader, "backpack", EquipmentItemSlot.Backpack);
                    AddEquipment(result, reader, "cosplay", EquipmentItemSlot.Cosplay);
                    AddEquipment(result, reader, "stabilizer", EquipmentItemSlot.Stabilizer);
                    return result;
                }
            }
        }

        private static void AddEquipment(
            ICollection<NativeCreationItem> target,
            SQLiteWrapperReader reader,
            string columnPrefix,
            EquipmentItemSlot slot)
        {
            var itemId = reader.GetUInt32(columnPrefix + "_id", 0);
            if (itemId == 0)
                return;
            target.Add(new NativeCreationItem(
                0,
                itemId,
                1,
                reader.GetByte(columnPrefix + "_grade_id"),
                SlotType.Equipment,
                (int)slot));
        }

        private static List<NativeCreationItem> ReadSupplies(
            SqliteConnection connection,
            byte ability)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT s.id,s.item_id,s.amount,s.grade_id,d.slot_index " +
                    "FROM character_supplies s " +
                    "JOIN native_character_creation_supply_slots d ON d.supply_id=s.id " +
                    "WHERE s.ability_id IN (0,@ability) ORDER BY d.slot_index,s.id";
                var parameter = command.CreateParameter();
                parameter.ParameterName = "@ability";
                parameter.Value = ability;
                command.Parameters.Add(parameter);
                var result = new List<NativeCreationItem>();
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        result.Add(new NativeCreationItem(
                            reader.GetUInt32("id"),
                            reader.GetUInt32("item_id"),
                            reader.GetInt32("amount"),
                            reader.GetByte("grade_id"),
                            SlotType.Inventory,
                            reader.GetInt32("slot_index")));
                    }
                }
                return result;
            }
        }

        private static List<uint> ReadSelectedSkills(
            SqliteConnection connection,
            byte ability)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT id FROM skills " +
                    "WHERE ability_id=@ability AND ability_level<=1 " +
                    "AND auto_learn=1 AND need_learn=1 AND show=1 " +
                    "ORDER BY id";
                var parameter = command.CreateParameter();
                parameter.ParameterName = "@ability";
                parameter.Value = ability;
                command.Parameters.Add(parameter);
                var result = new List<uint>();
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                        result.Add(reader.GetUInt32("id"));
                }
                if (result.Count != 1)
                    throw new InvalidOperationException(
                        $"AA8 initial ability {ability} expected one native start skill, found {result.Count}");
                return result;
            }
        }

        private static List<ActionSlot> ReadActions(
            SqliteConnection connection,
            uint characterId,
            byte ability)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT slot_index,action_type,action_id " +
                    "FROM native_character_creation_action_slots " +
                    "WHERE character_id=@character AND ability_id=@ability ORDER BY slot_index";
                var character = command.CreateParameter();
                character.ParameterName = "@character";
                character.Value = characterId;
                command.Parameters.Add(character);
                var selectedAbility = command.CreateParameter();
                selectedAbility.ParameterName = "@ability";
                selectedAbility.Value = ability;
                command.Parameters.Add(selectedAbility);
                var result = new List<ActionSlot>();
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    var expected = 0;
                    while (reader.Read())
                    {
                        var slot = reader.GetInt32("slot_index");
                        if (slot != expected++)
                            throw new InvalidOperationException(
                                $"AA8 action bar has a gap at {characterId}/{ability}/{slot}");
                        result.Add(new ActionSlot
                        {
                            Type = (ActionSlotType)reader.GetByte("action_type"),
                            ActionId = reader.GetUInt64("action_id")
                        });
                    }
                }
                if (result.Count != Character.MaxActionSlots)
                    throw new InvalidOperationException(
                        $"AA8 action bar expected {Character.MaxActionSlots} slots, found {result.Count}");
                return result;
            }
        }

        private static void ValidateReferencesAndSpace(
            NativeCreationTemplate template,
            IReadOnlyCollection<NativeCreationItem> equipment,
            IReadOnlyCollection<NativeCreationItem> supplies,
            IReadOnlyCollection<uint> selectedSkills,
            IReadOnlyCollection<ActionSlot> actions)
        {
            foreach (var item in equipment.Concat(supplies))
            {
                var itemTemplate = ItemManager.Instance.GetTemplate(item.TemplateId);
                if (itemTemplate == null)
                    throw new InvalidOperationException(
                        $"AA8 creation references missing item {item.TemplateId}");

                // Body-part definitions are concrete item templates backed by
                // item_body_parts rather than items. They intentionally have
                // no stack or enchant metadata; their only valid bootstrap
                // representation is one ungraded item in the matching
                // appearance slot.
                var validAmountAndGrade = itemTemplate is BodyPartTemplate
                    ? item.Amount == 1 && item.Grade == 0
                    : item.Amount > 0 &&
                      item.Amount <= itemTemplate.MaxCount &&
                      (itemTemplate.MaxEnchantableGrade <= 0 ||
                       item.Grade <= itemTemplate.MaxEnchantableGrade);
                if (!validAmountAndGrade)
                    throw new InvalidOperationException(
                        $"AA8 creation item {item.TemplateId} has invalid amount/grade");
                var probe = ItemManager.Instance.Create(
                    item.TemplateId, item.Amount, item.Grade, false);
                if (probe == null)
                    throw new InvalidOperationException(
                        $"AA8 creation item {item.TemplateId} is not materializable");
                if (item.Container == SlotType.Equipment)
                {
                    if (!EquipmentRuleService.Instance.CanOccupyPhysicalSlot(
                            probe, (EquipmentItemSlot)item.Slot))
                        throw new InvalidOperationException(
                            $"AA8 creation item {item.TemplateId} cannot occupy slot {item.Slot}");
                }
            }

            if (equipment.Select(x => x.Slot).Distinct().Count() != equipment.Count)
                throw new InvalidOperationException(
                    $"AA8 equipment slots collide for character {template.Id}");

            var main = equipment.FirstOrDefault(
                x => x.Slot == (int)EquipmentItemSlot.Mainhand);
            var offhand = equipment.FirstOrDefault(
                x => x.Slot == (int)EquipmentItemSlot.Offhand);
            if (main != null && offhand != null)
            {
                var probe = ItemManager.Instance.Create(
                    main.TemplateId, main.Amount, main.Grade, false);
                if (EquipmentRuleService.Instance.IsTwoHanded(probe))
                    throw new InvalidOperationException(
                        $"AA8 equip pack has two-hand/offhand conflict for character {template.Id}");
            }

            if (supplies.Select(x => x.Slot).Distinct().Count() != supplies.Count ||
                supplies.Any(x => x.Slot < 0 || x.Slot >= template.InventorySlots))
                throw new InvalidOperationException(
                    $"AA8 supplies exceed or collide in the native bag for character {template.Id}");

            foreach (var skillId in selectedSkills)
            {
                if (SkillManager.Instance.GetSkillTemplate(skillId) == null)
                    throw new InvalidOperationException(
                        $"AA8 creation references missing selected skill {skillId}");
            }

            foreach (var action in actions)
            {
                switch (action.Type)
                {
                    case ActionSlotType.None:
                        if (action.ActionId != 0)
                            throw new InvalidOperationException(
                                "AA8 empty action slot contains a reference");
                        break;
                    case ActionSlotType.ItemType:
                        if (action.ActionId > uint.MaxValue ||
                            ItemManager.Instance.GetTemplate((uint)action.ActionId) == null)
                            throw new InvalidOperationException(
                                $"AA8 action bar references missing item type {action.ActionId}");
                        break;
                    case ActionSlotType.Spell:
                    case ActionSlotType.RidePetSpell:
                    case ActionSlotType.BattlePetSpell:
                        if (action.ActionId > uint.MaxValue ||
                            SkillManager.Instance.GetSkillTemplate((uint)action.ActionId) == null)
                            throw new InvalidOperationException(
                                $"AA8 action bar references missing skill {action.ActionId}");
                        break;
                    case ActionSlotType.ItemId:
                        throw new InvalidOperationException(
                            "AA8 immutable bootstrap cannot contain a pre-allocation item instance id");
                    default:
                        throw new InvalidOperationException(
                            $"AA8 action bar contains unsupported action type {(byte)action.Type}");
                }
            }
        }
    }
}
