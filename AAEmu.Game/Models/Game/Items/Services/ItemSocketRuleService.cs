using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services;

public enum ItemSocketValidationFailure
{
    None,
    CatalogueUnavailable,
    InvalidTarget,
    DefinitionMissing,
    ExplicitItemMismatch,
    SlotMismatch,
    ItemLevelTooLow,
    SocketsFull,
    ChanceDefinitionMissing,
    ProbabilityUnavailable,
    UnsupportedNativeCriteria
}

public sealed class ItemSocketDefinition
{
    public uint Id { get; init; }
    public uint ItemId { get; init; }
    public uint EquipSlotGroupId { get; init; }
    public uint EquipItemId { get; init; }
    public uint EquipItemTagId { get; init; }
    public bool IgnoreEquipItemTag { get; init; }
    public uint ItemSocketChanceId { get; init; }
    public uint EisetId { get; init; }
}

public sealed class ItemSocketChanceDefinition
{
    public const int NativeChanceSlots = 10;

    public uint Id { get; init; }
    public bool FailBreak { get; init; }
    public uint CostRatio { get; init; }
    public int?[] SocketChances { get; } = new int?[NativeChanceSlots];

    /// <summary>
    /// Chance of installing the next Lunagem. r575 leaves <c>socket0</c> as a sentinel and uses
    /// <c>socket1</c> for the first install, through <c>socket9</c> for the ninth.
    /// </summary>
    public int? GetInstallChance(int occupiedSockets)
    {
        var chanceIndex = occupiedSockets + 1;
        return chanceIndex is > 0 and < NativeChanceSlots ? SocketChances[chanceIndex] : null;
    }

    public bool IsGuaranteed(int occupiedSockets, int count)
    {
        if (count <= 0)
            return false;
        for (var offset = 0; offset < count; offset++)
            if (GetInstallChance(occupiedSockets + offset) != 10000)
                return false;
        return true;
    }
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

/// <summary>
/// Data-driven r575 Lunagem eligibility, probability and cost rules.
/// </summary>
/// <remarks>
/// The retail compact carries the catalogue and cost ratios but zeros the probability columns. The
/// deployed compact must first be restored from the complete r575 database by
/// <c>Scripts/PatchAa10SocketChances.py</c>; zero/absent probabilities fail closed here.
/// </remarks>
public sealed class ItemSocketRuleService
{
    private readonly Dictionary<uint, ItemSocketDefinition> _definitions = [];
    private readonly Dictionary<uint, ItemSocketChanceDefinition> _chances = [];
    private readonly Dictionary<uint, int> _levelLimits = [];
    private readonly Dictionary<(uint SlotTypeId, uint GradeId), int> _socketLimits = [];
    private readonly Dictionary<uint, HashSet<uint>> _slotGroups = [];

    public static ItemSocketRuleService Instance { get; } = new();

    public bool NativeCatalogueAvailable { get; private set; }

    public void Clear()
    {
        NativeCatalogueAvailable = false;
        _definitions.Clear();
        _chances.Clear();
        _levelLimits.Clear();
        _socketLimits.Clear();
        _slotGroups.Clear();
    }

    public void MarkNativeCatalogueAvailable() => NativeCatalogueAvailable = true;

    public void RegisterDefinition(ItemSocketDefinition definition)
    {
        if (definition is not null)
            _definitions[definition.ItemId] = definition;
    }

    public void RegisterChance(ItemSocketChanceDefinition definition)
    {
        if (definition is not null)
            _chances[definition.Id] = definition;
    }

    public void RegisterLevelLimit(uint itemId, int level) => _levelLimits[itemId] = level;

    public void RegisterSocketLimit(uint slotTypeId, uint gradeId, int maximum) =>
        _socketLimits[(slotTypeId, gradeId)] = maximum;

    public void RegisterSlotGroupMember(uint groupId, uint slotTypeId)
    {
        if (!_slotGroups.TryGetValue(groupId, out var members))
        {
            members = [];
            _slotGroups[groupId] = members;
        }

        members.Add(slotTypeId);
    }

    public ItemSocketDefinition GetDefinition(uint itemId) =>
        _definitions.GetValueOrDefault(itemId);

    public ItemSocketValidationResult Validate(EquipItem target, Item reagent)
    {
        var result = new ItemSocketValidationResult();
        if (!NativeCatalogueAvailable)
            return Fail(result, ItemSocketValidationFailure.CatalogueUnavailable,
                "The native AA10 socket catalogue is not active.");
        if (target is null || reagent is null)
            return Fail(result, ItemSocketValidationFailure.InvalidTarget,
                "The target or Lunagem is invalid.");
        if (!_definitions.TryGetValue(reagent.TemplateId, out var definition))
            return Fail(result, ItemSocketValidationFailure.DefinitionMissing,
                $"Item {reagent.TemplateId} has no r575 item_sockets row.");

        result.Definition = definition;
        result.OccupiedSockets = target.OccupiedNativeSocketCount;

        if (definition.EquipItemId != 0 && definition.EquipItemId != target.TemplateId)
            return Fail(result, ItemSocketValidationFailure.ExplicitItemMismatch,
                $"The Lunagem is restricted to item {definition.EquipItemId}.");

        if (!TryGetSlotTypeId(target.Template, out var slotTypeId))
            return Fail(result, ItemSocketValidationFailure.InvalidTarget,
                $"Target item {target.TemplateId} has no equipment slot type.");

        if (definition.EquipSlotGroupId != 0 &&
            (!_slotGroups.TryGetValue(definition.EquipSlotGroupId, out var allowedSlots) ||
             !allowedSlots.Contains(slotTypeId)))
            return Fail(result, ItemSocketValidationFailure.SlotMismatch,
                $"Slot {slotTypeId} is not in group {definition.EquipSlotGroupId}.");

        if (_levelLimits.TryGetValue(reagent.TemplateId, out var requiredLevel) &&
            target.Template.Level < requiredLevel)
            return Fail(result, ItemSocketValidationFailure.ItemLevelTooLow,
                $"Target level {target.Template.Level} is below {requiredLevel}.");

        // These criteria need their own native consumers. Do not silently broaden eligibility.
        if (definition.EisetId != 0 ||
            (definition.EquipItemTagId != 0 && !definition.IgnoreEquipItemTag))
            return Fail(result, ItemSocketValidationFailure.UnsupportedNativeCriteria,
                "This Lunagem depends on an unresolved eiset/item-tag criterion.");

        if (!_socketLimits.TryGetValue((slotTypeId, target.Grade), out var maximumSockets))
            return Fail(result, ItemSocketValidationFailure.UnsupportedNativeCriteria,
                $"No socket limit exists for slot {slotTypeId}, grade {target.Grade}.");

        result.MaximumSockets = Math.Min(maximumSockets, EquipItem.NativeSocketCapacity);
        if (result.OccupiedSockets >= result.MaximumSockets)
            return Fail(result, ItemSocketValidationFailure.SocketsFull,
                $"The target already has {result.OccupiedSockets}/{result.MaximumSockets} sockets.");

        if (!_chances.TryGetValue(definition.ItemSocketChanceId, out var chanceDefinition))
            return Fail(result, ItemSocketValidationFailure.ChanceDefinitionMissing,
                $"Chance profile {definition.ItemSocketChanceId} is absent.");

        result.ChanceDefinition = chanceDefinition;
        result.SuccessChance = chanceDefinition.GetInstallChance(result.OccupiedSockets);
        if (result.SuccessChance is null or <= 0)
            return Fail(result, ItemSocketValidationFailure.ProbabilityUnavailable,
                $"Chance profile {chanceDefinition.Id} has no usable probability for socket " +
                $"{result.OccupiedSockets + 1}.");

        return result;
    }

    public bool TryCalculateCost(
        Character character,
        EquipItem target,
        Item reagent,
        ItemSocketValidationResult validation,
        int occupiedSockets,
        out int cost)
    {
        cost = 0;
        if (character is null || target is null || reagent is null ||
            validation?.ChanceDefinition is null || occupiedSockets < 0)
            return false;

        var formula = FormulaManager.Instance.GetFormula((uint)FormulaKind.ItemSocketingCost);
        if (formula is null)
            return false;

        var parameters = new Dictionary<string, double>
        {
            ["item_level"] = target.Template.Level,
            ["socket_item_level"] = reagent.Template.Level,
            ["item_used_socket"] = occupiedSockets,
            // r575 defines this unit attribute after the subset currently decoded by rama_10.
            // Until that catalogue is expanded, no active modifier is equivalent to the native zero.
            ["item_socketing_cost_mul"] = 0d
        };
        var formulaValue = formula.Evaluate(parameters);
        if (double.IsNaN(formulaValue) || double.IsInfinity(formulaValue) || formulaValue < 0)
            return false;

        var finalValue = formulaValue * validation.ChanceDefinition.CostRatio * 0.01d;
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
            case WeaponTemplate { HoldableTemplate: not null } weapon:
                slotTypeId = weapon.HoldableTemplate.SlotTypeId;
                return true;
            case ArmorTemplate { SlotTemplate: not null } armor:
                slotTypeId = armor.SlotTemplate.SlotTypeId;
                return true;
            case AccessoryTemplate { SlotTemplate: not null } accessory:
                slotTypeId = accessory.SlotTemplate.SlotTypeId;
                return true;
            default:
                slotTypeId = 0;
                return false;
        }
    }
}
