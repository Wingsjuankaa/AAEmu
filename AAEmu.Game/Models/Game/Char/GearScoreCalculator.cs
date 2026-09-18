using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// Server-side gear score, matching the client's own display math.
///
/// Per equipped piece, one of the shipped <c>formulas</c> rows is evaluated:
/// kind 30 (weapons, from holdables), kind 56 (armor), kind 57 (accessories) —
/// then kind 31 per Lunagem and kind 32 once for the installed Lunafrost, using
/// each augmentation's template level (r575 FUN_39b4cc60).
/// </summary>
public static class GearScoreCalculator
{
    /// <summary>World/level scaling factor; 1.0 until scaled content exists.</summary>
    public const double DefaultScalingMultiplier = 1.0;

    /// <summary>
    /// Gear score of one equipped piece, or 0 when the piece is not gear.
    /// </summary>
    public static double EvaluateItem(Item item)
    {
        if (item is not EquipItem equip || equip.Template is not ItemTemplate template)
            return 0;

        var level = equip.EffectiveStatLevel;
        // Grade channel multiplier (0.8 poor .. 2.1 arche-eternal); all var_* columns agree per row.
        var gradeTemplate = ItemManager.Instance.GetGradeTemplate(equip.Grade);
        var gradeMultiplier = gradeTemplate?.HoldableDps ?? 1.0;

        var parameters = new Dictionary<string, double>
        {
            ["item_level"] = level,
            ["item_grade"] = gradeMultiplier,
            ["scaling_multiplier"] = ItemEnchantScaleService.Instance.Get(equip.ScaledA) is { } ratio
                ? (float)((1000f + ratio.Scale) * 0.001f) : 0,
            ["element_level"] = equip.ElementLevel,
        };

        FormulaKind kind;
        switch (template)
        {
            case WeaponTemplate weapon:
                parameters["gear_score_multiplier"] = FromStoredMultiplier(ItemManager.Instance.GetHoldable(weapon.HoldableTemplate?.Id ?? 0)?.GearScoreMultiplier ?? 0);
                kind = FormulaKind.GearScoreWeaponArmorAcc;
                break;
            case ArmorTemplate armor:
                parameters["gear_score_multiplier"] = FromStoredMultiplier(ItemManager.Instance.GetWearableSlot(armor.SlotTemplate?.SlotTypeId ?? 0)?.GearScoreMultiplier ?? 0);
                kind = FormulaKind.GearScoreArmor;
                break;
            case AccessoryTemplate accessory:
                parameters["gear_score_multiplier"] = FromStoredMultiplier(ItemManager.Instance.GetWearableSlot(accessory.SlotTemplate?.SlotTypeId ?? 0)?.GearScoreMultiplier ?? 0);
                kind = FormulaKind.GearScoreAccessory;
                break;
            default:
                return 0; // non-equip gear (cosmetics, backpacks) carries no score
        }

        var score = NativeComponent(FormulaManager.Instance.GetFormula((uint)kind)?.Evaluate(parameters) ?? 0);
        return AddAugmentations(score, equip,
            id => ItemManager.Instance.GetItemTemplateFromItemId(id),
            (formula, augmentationLevel) => FormulaManager.Instance.GetFormula((uint)formula)?.Evaluate(
                new Dictionary<string, double> { ["item_level"] = augmentationLevel }) ?? 0);
    }

    /// <summary>
    /// Total gear score across a character's equipped pieces.
    /// </summary>
    public static int Evaluate(Character character)
    {
        if (character?.Inventory?.Equipment == null)
            return 0;

        float total = 0;
        foreach (var item in character.Inventory.Equipment.Items.OrderBy(item => item?.Slot))
        {
            if (item != null && IsScoredSlot(item.Slot))
                total += (float)EvaluateItem(item);
        }

        return (int)total;
    }

    // FUN_39985880/B0/D0 and exclusions in FUN_39b4e1c0.
    internal static bool IsScoredSlot(int slot) => slot is >= 0 and <= 18 or 26 or 27 or 29 or 30 or 32;

    // FUN_39979340/39979460/39979530 floor each float result to one decimal.
    internal static float NativeComponent(double value) => MathF.Floor((float)value * 10f) / 10f;

    internal static float AddAugmentations(float score, EquipItem equip,
        Func<uint, ItemTemplate> findTemplate, Func<FormulaKind, int, double> evaluate)
    {
        // Native detail +0x08 is PISC GemData[1], separate from the nine sockets.
        if (equip.GemData is { Length: > 1 } && equip.GemData[1] != 0 &&
            findTemplate(equip.GemData[1]) is { } frost)
            score += NativeComponent(evaluate(FormulaKind.GearScoreEnchantingGem, frost.Level));
        foreach (var id in equip.NativeSocketItemIds)
            if (id != 0 && findTemplate(id) is { } gem)
                score += NativeComponent(evaluate(FormulaKind.GearScoreSocket, gem.Level));
        return score;
    }

    /// <summary>
    /// The gear-score multiplier a template column carries, in the units the shipped formulas use.
    /// </summary>
    /// <remarks>
    /// The columns store the multiplier <b>per hundred</b>: a weapon that weighs 2.2 in formula 30 is
    /// stored as 220, an armor slot that weighs 0.78 in formula 56 as 78, and the two cosmetic tiers
    /// formula 56 singles out — the ones it compares against 0.01 and 0.02 — as 1 and 2. Feeding the
    /// stored number straight into a formula that expects the fraction inflates every piece a hundredfold,
    /// which is a hundredfold on the character's total.
    /// </remarks>
    public static double FromStoredMultiplier(int stored) => stored / 100.0;
}
