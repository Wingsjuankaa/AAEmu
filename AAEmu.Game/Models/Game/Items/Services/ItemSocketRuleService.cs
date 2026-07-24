using System;
using System.Collections.Generic;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public enum ItemSocketDefinitionKind
    {
        EnchantingGem,
        Lunagem
    }

    public enum ItemSocketValidationFailure
    {
        None,
        CatalogueUnavailable,
        InvalidTarget,
        DefinitionMissing,
        ExplicitItemMismatch,
        SlotMismatch,
        GradeTooLow,
        ItemLevelTooLow,
        SocketsFull,
        ChanceDefinitionMissing,
        ProbabilityUnavailable,
        UnsupportedNativeCriteria
    }

    public sealed class ItemSocketDefinition
    {
        public uint Id { get; set; }
        public uint ItemId { get; set; }
        public ItemSocketDefinitionKind Kind { get; set; }
        public string BuffModifierTooltip { get; set; } = string.Empty;
        public uint EisetId { get; set; }
        public uint EquipItemTagId { get; set; }
        public uint EquipItemId { get; set; }
        public byte EquipLevel { get; set; }
        public uint EquipSlotGroupId { get; set; }
        public uint GemVisualEffectId { get; set; }
        public bool Extractable { get; set; }
        public bool IgnoreEquipItemTag { get; set; }
        public uint ItemGradeId { get; set; }
        public uint ItemSocketChanceId { get; set; }
        public string SkillModifierTooltip { get; set; } = string.Empty;
    }

    public sealed class ItemSocketChanceDefinition
    {
        public uint Id { get; set; }
        public bool FailBreak { get; set; }
        public uint CostRatio { get; set; }
        public int?[] SocketChances { get; } = new int?[10];

        public int? GetChance(int occupiedSockets)
        {
            return occupiedSockets >= 0 && occupiedSockets < SocketChances.Length
                ? SocketChances[occupiedSockets]
                : null;
        }
    }

    public sealed class ItemSocketChangeDefinition
    {
        public uint Id { get; set; }
        public uint EnchantItemId { get; set; }
        public uint SourceItemId { get; set; }
        public uint TargetItemId { get; set; }
    }

    public sealed class ItemSocketValidationResult
    {
        public ItemSocketValidationFailure Failure { get; set; }
        public string Reason { get; set; } = string.Empty;
        public ItemSocketDefinition Definition { get; set; }
        public ItemSocketChanceDefinition ChanceDefinition { get; set; }
        public int OccupiedSockets { get; set; }
        public int MaximumSockets { get; set; }
        public int? SuccessChance { get; set; }
        public bool IsValid => Failure == ItemSocketValidationFailure.None;
    }

    public interface IItemSocketRuleService
    {
        bool NativeCatalogueAvailable { get; }
        void Clear();
        void MarkNativeCatalogueAvailable();
        void RegisterDefinition(ItemSocketDefinition definition);
        void RegisterChance(ItemSocketChanceDefinition definition);
        void RegisterChange(ItemSocketChangeDefinition definition);
        void RegisterLevelLimit(uint itemId, int level);
        void RegisterSocketLimit(uint slotTypeId, uint gradeId, int maximum);
        void RegisterSlotGroupMember(uint groupId, uint slotTypeId);
        ItemSocketDefinition GetDefinition(uint itemId);
        ItemSocketChangeDefinition GetChange(uint enchantItemId, uint sourceItemId);
        ItemSocketValidationResult Validate(EquipItem target, Item reagent);
        bool TryCalculateCost(
            Character character,
            EquipItem target,
            Item reagent,
            ItemSocketValidationResult validation,
            out int cost);
    }

    /// <summary>
    /// Native AA8 socket/lunagem validation. This service deliberately blocks
    /// operations whose probability or criteria have not been recovered from
    /// the AA8 client instead of falling back to historical compact data.
    /// </summary>
    public sealed class ItemSocketRuleService : IItemSocketRuleService
    {
        private readonly Dictionary<uint, ItemSocketDefinition> _definitions = new();
        private readonly Dictionary<uint, ItemSocketChanceDefinition> _chances = new();
        private readonly Dictionary<(uint EnchantItemId, uint SourceItemId), ItemSocketChangeDefinition> _changes = new();
        private readonly Dictionary<uint, int> _levelLimits = new();
        private readonly Dictionary<(uint SlotTypeId, uint GradeId), int> _socketLimits = new();
        private readonly Dictionary<uint, HashSet<uint>> _slotGroups = new();

        public static ItemSocketRuleService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _definitions.Clear();
            _chances.Clear();
            _changes.Clear();
            _levelLimits.Clear();
            _socketLimits.Clear();
            _slotGroups.Clear();
        }

        public void MarkNativeCatalogueAvailable()
        {
            NativeCatalogueAvailable = true;
        }

        public void RegisterDefinition(ItemSocketDefinition definition)
        {
            if (definition != null)
                _definitions[definition.ItemId] = definition;
        }

        public void RegisterChance(ItemSocketChanceDefinition definition)
        {
            if (definition != null)
                _chances[definition.Id] = definition;
        }

        public void RegisterChange(ItemSocketChangeDefinition definition)
        {
            if (definition != null)
                _changes[(definition.EnchantItemId, definition.SourceItemId)] = definition;
        }

        public void RegisterLevelLimit(uint itemId, int level)
        {
            _levelLimits[itemId] = level;
        }

        public void RegisterSocketLimit(uint slotTypeId, uint gradeId, int maximum)
        {
            _socketLimits[(slotTypeId, gradeId)] = maximum;
        }

        public void RegisterSlotGroupMember(uint groupId, uint slotTypeId)
        {
            if (!_slotGroups.TryGetValue(groupId, out var members))
            {
                members = new HashSet<uint>();
                _slotGroups[groupId] = members;
            }

            members.Add(slotTypeId);
        }

        public ItemSocketDefinition GetDefinition(uint itemId)
        {
            return _definitions.TryGetValue(itemId, out var definition) ? definition : null;
        }

        public ItemSocketChangeDefinition GetChange(uint enchantItemId, uint sourceItemId)
        {
            return _changes.TryGetValue((enchantItemId, sourceItemId), out var definition)
                ? definition
                : null;
        }

        public ItemSocketValidationResult Validate(EquipItem target, Item reagent)
        {
            var result = new ItemSocketValidationResult();
            if (!NativeCatalogueAvailable)
                return Fail(result, ItemSocketValidationFailure.CatalogueUnavailable,
                    "The native AA8 socket catalogue is not active.");
            if (target == null || reagent == null)
                return Fail(result, ItemSocketValidationFailure.InvalidTarget,
                    "The target or socket reagent is invalid.");
            if (!_definitions.TryGetValue(reagent.TemplateId, out var definition))
                return Fail(result, ItemSocketValidationFailure.DefinitionMissing,
                    $"Item {reagent.TemplateId} has no native AA8 socket definition.");

            result.Definition = definition;
            result.OccupiedSockets = target.OccupiedNativeSocketCount;

            if (definition.EquipItemId != 0 && definition.EquipItemId != target.TemplateId)
                return Fail(result, ItemSocketValidationFailure.ExplicitItemMismatch,
                    $"The reagent is restricted to item {definition.EquipItemId}.");

            if (!TryGetSlotTypeId(target.Template, out var slotTypeId))
                return Fail(result, ItemSocketValidationFailure.InvalidTarget,
                    $"Target item {target.TemplateId} has no confirmed AA8 equipment slot.");

            if (definition.EquipSlotGroupId != 0 &&
                (!_slotGroups.TryGetValue(definition.EquipSlotGroupId, out var allowedSlots) ||
                 !allowedSlots.Contains(slotTypeId)))
                return Fail(result, ItemSocketValidationFailure.SlotMismatch,
                    $"Slot type {slotTypeId} is not in AA8 slot group {definition.EquipSlotGroupId}.");

            if (definition.ItemGradeId != 0 && target.Grade < definition.ItemGradeId)
                return Fail(result, ItemSocketValidationFailure.GradeTooLow,
                    $"Target grade {target.Grade} is below required grade {definition.ItemGradeId}.");

            if (_levelLimits.TryGetValue(reagent.TemplateId, out var requiredLevel) &&
                target.Template.Level < requiredLevel)
                return Fail(result, ItemSocketValidationFailure.ItemLevelTooLow,
                    $"Target item level {target.Template.Level} is below required level {requiredLevel}.");

            // eiset/tag semantics affect eligibility. Until their AA8 consumers
            // are confirmed, isolate only definitions that depend on them.
            if (definition.EisetId != 0 ||
                (definition.EquipItemTagId != 0 && !definition.IgnoreEquipItemTag))
                return Fail(result, ItemSocketValidationFailure.UnsupportedNativeCriteria,
                    "This reagent uses AA8 eiset/item-tag criteria that are not decoded yet.");

            if (definition.Kind == ItemSocketDefinitionKind.EnchantingGem)
            {
                // AA8 exposes enchanting gems as the single "gemInfo" field,
                // not as one of the nine socketInfo entries. Replacing this
                // value therefore does not consume socket capacity.
                result.MaximumSockets = 1;
                result.OccupiedSockets = target.EnchantingGemItemId == 0 ? 0 : 1;
                result.SuccessChance = 10000;
                return result;
            }

            if (!_socketLimits.TryGetValue((slotTypeId, target.Grade), out var maximumSockets))
                return Fail(result, ItemSocketValidationFailure.UnsupportedNativeCriteria,
                    $"No AA8 socket limit exists for slot {slotTypeId} and grade {target.Grade}.");

            result.MaximumSockets = Math.Min(maximumSockets, EquipItem.NativeSocketCapacity);
            if (result.OccupiedSockets >= result.MaximumSockets)
                return Fail(result, ItemSocketValidationFailure.SocketsFull,
                    $"The target already has {result.OccupiedSockets}/{result.MaximumSockets} sockets.");

            if (!_chances.TryGetValue(definition.ItemSocketChanceId, out var chanceDefinition))
                return Fail(result, ItemSocketValidationFailure.ChanceDefinitionMissing,
                    $"AA8 chance definition {definition.ItemSocketChanceId} is absent.");

            result.ChanceDefinition = chanceDefinition;
            result.SuccessChance = chanceDefinition.GetChance(result.OccupiedSockets);
            if (!result.SuccessChance.HasValue)
                return Fail(result, ItemSocketValidationFailure.ProbabilityUnavailable,
                    $"AA8 did not expose socket{result.OccupiedSockets} for chance set {chanceDefinition.Id}.");

            return result;
        }

        public bool TryCalculateCost(
            Character character,
            EquipItem target,
            Item reagent,
            ItemSocketValidationResult validation,
            out int cost)
        {
            cost = 0;
            if (character == null || target == null || reagent == null ||
                validation == null || validation.Definition == null)
                return false;

            // Enchanting gems use the separate guaranteed gemInfo operation.
            if (validation.Definition.Kind == ItemSocketDefinitionKind.EnchantingGem)
                return true;
            if (validation.ChanceDefinition == null)
                return false;

            var formula =
                FormulaManager.Instance.GetFormula((uint)FormulaKind.ItemSocketingCost);
            if (formula == null)
                return false;

            var parameters = new Dictionary<string, double>
            {
                ["item_level"] = target.Template.Level,
                ["socket_item_level"] = reagent.Template.Level,
                ["item_used_socket"] = validation.OccupiedSockets,
                ["item_socketing_cost_mul"] =
                    character.GetAttribute<float>(
                        UnitAttribute.ItemSocketingCostMul,
                        0f)
            };
            var formulaValue = formula.Evaluate(parameters);
            if (double.IsNaN(formulaValue) || double.IsInfinity(formulaValue) ||
                formulaValue < 0)
                return false;

            // x2game FUN_39a4dde0 evaluates FormulaKind 38, applies the chance
            // set cost_ratio as a percentage, then rounds with +0.5.
            var finalValue =
                formulaValue * validation.ChanceDefinition.CostRatio * 0.01d;
            if (finalValue > int.MaxValue)
                return false;

            cost = (int)(finalValue + 0.5d);
            return true;
        }

        private static ItemSocketValidationResult Fail(
            ItemSocketValidationResult result,
            ItemSocketValidationFailure failure,
            string reason)
        {
            result.Failure = failure;
            result.Reason = reason;
            return result;
        }

        private static bool TryGetSlotTypeId(ItemTemplate template, out uint slotTypeId)
        {
            switch (template)
            {
                case WeaponTemplate weapon when weapon.HoldableTemplate != null:
                    slotTypeId = weapon.HoldableTemplate.SlotTypeId;
                    return true;
                case ArmorTemplate armor when armor.SlotTemplate != null:
                    slotTypeId = armor.SlotTemplate.SlotTypeId;
                    return true;
                case AccessoryTemplate accessory when accessory.SlotTemplate != null:
                    slotTypeId = accessory.SlotTemplate.SlotTypeId;
                    return true;
                default:
                    slotTypeId = 0;
                    return false;
            }
        }
    }
}
