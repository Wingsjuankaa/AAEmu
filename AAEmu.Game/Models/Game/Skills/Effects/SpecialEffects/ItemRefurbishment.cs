using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Temper/Refurbishment (special effect 126). The catalyst's value1 selects weapon (1) or armor
/// (2), value2 enables the shining catalyst's possible two-step Great Success, and value4 is the
/// highest scale descriptor the catalyst supports (+30 in the retail catalogue).
/// </summary>
public class ItemRefurbishment : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemRefurbishment;

    internal static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.itemCapScale);

    public override void Execute(BaseUnit caster,
        SkillCaster casterObj,
        BaseUnit target,
        SkillCastTarget targetObj,
        CastAction castObj,
        Skill skill,
        SkillObject skillObject,
        DateTime time,
        int value1,
        int value2,
        int value3,
        int value4)
    {
        if (caster is not Character character || !IsFeatureEnabled(FeaturesManager.Fsets))
        {
            Cancel(skill);
            return;
        }

        if (casterObj is not SkillItem catalystCaster ||
            targetObj is not SkillCastItemTarget targetItem)
        {
            Reject(character, skill, "unexpected caster or target wire shape");
            return;
        }

        var catalyst = character.Inventory.GetItemById(catalystCaster.ItemId);
        if (catalyst is null || catalyst.TemplateId != catalystCaster.ItemTemplateId || catalyst.Count < 1)
        {
            Reject(character, skill, "catalyst is no longer available");
            return;
        }

        var item = character.Inventory.GetItemById(targetItem.Id);
        if (item is null || item.OwnerId != character.Id)
        {
            Reject(character, skill, "target is no longer available");
            return;
        }

        Item supportItem = null;
        var supportTemplateId = 0u;
        var autoUseAaPoint = false;
        if (skillObject is SkillObjectItemGradeEnchantingSupport supportObject)
        {
            autoUseAaPoint = supportObject.AutoUseAaPoint;
            if (supportObject.SupportItemId != 0)
            {
                supportItem = character.Inventory.GetItemById(supportObject.SupportItemId);
                if (supportItem is null || supportItem.Count < 1 || supportItem._holdingContainer is null)
                {
                    Reject(character, skill, "selected support item is unavailable");
                    return;
                }
                supportTemplateId = supportItem.TemplateId;
            }
        }

        var service = ItemEnchantScaleService.Instance;
        if (!service.TryCreateAttempt(item, value1, value2 != 0, value4, supportTemplateId,
                out var attempt, out var failure))
        {
            Reject(character, skill, failure);
            return;
        }

        // r575 currently has no Break/Disable probability in any reachable row. Keep this
        // fail-closed if future catalogue data introduces either state mutation.
        if (attempt.Probabilities.BreakRatio != 0 || attempt.Probabilities.DisableRatio != 0)
        {
            Reject(character, skill, "destructive Temper outcome is not implemented");
            return;
        }

        if (!TryCalculateCost(character, item, attempt.Ratio, out var cost))
        {
            Reject(character, skill, "cost formula could not be resolved");
            return;
        }

        if (!character.TryPayCurrency(attempt.Ratio.CurrencyId, cost, autoUseAaPoint,
                ItemTaskType.Refurbishment))
        {
            Cancel(skill);
            return;
        }

        if (supportItem is not null &&
            supportItem._holdingContainer.ConsumeItem(ItemTaskType.Refurbishment,
                supportItem.TemplateId, 1, supportItem) != 1)
        {
            RefundCost(character, attempt.Ratio.CurrencyId, cost, autoUseAaPoint);
            Logger.Error("ItemRefurbishment: support {0}/{1} vanished after validation for {2}",
                supportItem.Id, supportItem.TemplateId, character.Name);
            Cancel(skill);
            return;
        }

        var downgradeRoll = attempt.Ratio.DownMax > 0
            ? Random.Shared.Next(1, attempt.Ratio.DownMax + 1)
            : 1;
        var outcome = service.ResolveOutcome(attempt,
            Random.Shared.Next(ItemEnchantScaleService.ProbabilityBase), downgradeRoll);

        if (outcome.AfterScaleId != attempt.BeforeScaleId)
        {
            ((EquipItem)item).ScaledA = outcome.AfterScaleId;

            if (item.SlotType == SlotType.Equipment)
                character.UpdateGearBonuses(null, null);

            // ScaleCap (127) is the native task which refreshes the item's 0x3C descriptor and
            // releases the UI for another consecutive attempt.
            character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.Refurbishment,
                [new ItemUpdate(item)], []));
            character.SendPacket(new SCItemDetailUpdatedPacket(item));
        }

        character.SendPacket(new SCItemRefurbishmentResultPacket(outcome.Result, item,
            attempt.BeforeScaleId, outcome.AfterScaleId));

        Logger.Info(
            "ItemRefurbishment: character={0}, item={1}/{2}, catalyst={3}, support={4}, " +
            "scale={5}->{6}, result={7}, cost={8}, success={9}, great={10}, down={11}",
            character.Name, item.Id, item.TemplateId, catalyst.TemplateId, supportTemplateId,
            attempt.BeforeScaleId, outcome.AfterScaleId, outcome.Result, cost,
            attempt.Probabilities.SuccessRatio, attempt.Probabilities.GreatSuccessRatio,
            attempt.Probabilities.DowngradeRatio);
    }

    private static bool TryCalculateCost(Character character, Item item, EnchantScaleRatio ratio,
        out int cost)
    {
        cost = 0;
        if (!TryGetSlotTypeId(item.Template, out var slotTypeId))
            return false;

        var slotCost = ItemManager.Instance.GetEquipSlotEnchantingCost(slotTypeId);
        var formula = FormulaManager.Instance.GetFormula((uint)FormulaKind.EnchantScaleCost);
        if (slotCost is null || formula is null)
            return false;

        var value = formula.Evaluate(new Dictionary<string, double>
        {
            ["item_level"] = item.Template.Level,
            ["scale_cost"] = ratio.Cost,
            ["equip_slot_enchant_cost"] = slotCost.Cost,
            ["enchant_scale_cost_mul"] = character.GetEnchantScaleCostMultiplier()
        });
        if (double.IsNaN(value) || double.IsInfinity(value) || value < 0 || value > int.MaxValue)
            return false;

        cost = (int)(value + 0.5d);
        return true;
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
            default:
                slotTypeId = 0;
                return false;
        }
    }

    private static void RefundCost(Character character, uint currencyId, long cost,
        bool autoUseAaPoint)
    {
        if (cost <= 0)
            return;

        var refunded = (ContentCurrencyType)currencyId switch
        {
            ContentCurrencyType.Gold or ContentCurrencyType.GoldWithAaPoint => autoUseAaPoint
                ? character.AddAAPoint(SlotType.Inventory, cost)
                : character.AddMoney(SlotType.Inventory, cost),
            ContentCurrencyType.AaPoint => character.AddAAPoint(SlotType.Inventory, cost),
            _ => false
        };

        if (!refunded)
            Logger.Error("ItemRefurbishment: could not refund {0} of currency {1} to {2}",
                cost, currencyId, character.Name);
    }

    private static void Reject(Character character, Skill skill, string reason)
    {
        Logger.Warn("ItemRefurbishment rejected for {0}: {1}", character.Name, reason);
        character.SendErrorMessage(ErrorMessageType.Invalid);
        Cancel(skill);
    }

    private static void Cancel(Skill skill)
    {
        if (skill is not null)
            skill.Cancelled = true;
    }
}
