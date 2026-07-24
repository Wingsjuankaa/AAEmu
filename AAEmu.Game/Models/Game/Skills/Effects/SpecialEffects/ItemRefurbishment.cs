using System;
using System.Collections.Generic;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemRefurbishment : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType =>
            SpecialType.ItemRefurbishment;

        public override void Execute(
            Unit caster,
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
            if (caster is not Character character ||
                casterObj is not SkillItem catalystCaster ||
                targetObj is not SkillCastItemTarget targetItem)
            {
                Cancel(skill);
                return;
            }

            var catalyst = character.Inventory.GetItemById(catalystCaster.ItemId);
            if (catalyst == null ||
                catalyst.TemplateId != catalystCaster.ItemTemplateId ||
                catalyst.Count < 1)
            {
                Reject(character, skill, "The AA8 temper catalyst is no longer available.");
                return;
            }

            var item = character.Inventory.GetItemById(targetItem.Id);
            if (item == null || item.OwnerId != character.Id)
            {
                Reject(character, skill, "The AA8 temper target is no longer available.");
                return;
            }

            Item supportItem = null;
            var supportTemplateId = 0u;
            if (skillObject is SkillObjectItemGradeEnchantingSupport supportObject &&
                supportObject.SupportItemId != 0)
            {
                supportItem = character.Inventory.GetItemById(supportObject.SupportItemId);
                if (supportItem == null ||
                    supportItem.Count < 1 ||
                    supportItem._holdingContainer == null)
                {
                    Reject(character, skill, "The selected AA8 temper support is unavailable.");
                    return;
                }
                supportTemplateId = supportItem.TemplateId;
            }

            var service = ItemEnchantScaleService.Instance;
            if (!service.TryCreateAttempt(
                    item,
                    value1,
                    value2 != 0,
                    supportTemplateId,
                    out var attempt,
                    out var failure))
            {
                Reject(character, skill, failure);
                return;
            }

            // The active Kakao 8.0 ratios have no break/disable outcomes. Keep
            // future destructive rows fail-closed until their AA8 item-state
            // mutation is independently confirmed.
            if (attempt.Probabilities.BreakRatio != 0 ||
                attempt.Probabilities.DisableRatio != 0)
            {
                Reject(
                    character,
                    skill,
                    "This native temper tier has an unsupported destructive outcome.");
                return;
            }

            if (attempt.Ratio.CurrencyId != 0)
            {
                Reject(
                    character,
                    skill,
                    $"Unsupported AA8 temper currency {attempt.Ratio.CurrencyId}.");
                return;
            }

            if (!TryCalculateCost(character, item, attempt.Ratio, out var cost))
            {
                Reject(character, skill, "The AA8 temper cost could not be resolved.");
                return;
            }
            if (character.Money < cost)
            {
                character.SendErrorMessage(ErrorMessageType.NotEnoughMoney);
                Cancel(skill);
                return;
            }

            var downgradeRoll = attempt.Ratio.DownMax > 0
                ? Rand.Next(1, attempt.Ratio.DownMax + 1)
                : 1;
            var outcome = service.ResolveOutcome(
                attempt,
                Rand.Next(0, ItemEnchantScaleService.ProbabilityBase),
                downgradeRoll);

            // All validation is complete before the first mutation. Character
            // actions run on the game loop, so these state changes cannot be
            // interleaved by a second inventory request.
            if (!character.SubtractMoney(SlotType.Inventory, cost, ItemTaskType.Refurbishment))
            {
                Cancel(skill);
                return;
            }

            if (supportItem != null &&
                supportItem._holdingContainer.ConsumeItem(
                    ItemTaskType.Refurbishment,
                    supportItem.TemplateId,
                    1,
                    supportItem) != 1)
            {
                character.AddMoney(SlotType.Inventory, cost, ItemTaskType.Refurbishment);
                Reject(character, skill, "The AA8 temper support changed during execution.");
                return;
            }

            if (outcome.Result == ItemRefurbishmentResult.Downgrade ||
                outcome.Result == ItemRefurbishmentResult.Success ||
                outcome.Result == ItemRefurbishmentResult.GreatSuccess)
            {
                item.ScaledA = outcome.AfterScaleId;
                character.SendPacket(
                    new SCItemTaskSuccessPacket(
                        ItemTaskType.Refurbishment,
                        new ItemUpdate(item),
                        new List<ulong>()));

                if (item.SlotType == SlotType.Equipment)
                    EquipmentSyncService.Instance.Resync(character);
            }

            character.SendPacket(
                new SCItemRefurbishmentResultPacket(
                    outcome.Result,
                    item,
                    attempt.BeforeScaleId,
                    outcome.AfterScaleId));

            _log.Info(
                "AA8 temper: character={0}, item={1}/{2}, catalyst={3}, support={4}, " +
                "before={5}, after={6}, result={7}, cost={8}, " +
                "success={9}, great={10}, down={11}",
                character.Name,
                item.Id,
                item.TemplateId,
                catalyst.TemplateId,
                supportTemplateId,
                attempt.BeforeScaleId,
                outcome.AfterScaleId,
                outcome.Result,
                cost,
                attempt.Probabilities.SuccessRatio,
                attempt.Probabilities.GreatSuccessRatio,
                attempt.Probabilities.DowngradeRatio);
        }

        private static bool TryCalculateCost(
            Character character,
            Item item,
            EnchantScaleRatio ratio,
            out int cost)
        {
            cost = 0;
            if (!TryGetSlotTypeId(item.Template, out var slotTypeId))
                return false;
            var slotCost = ItemManager.Instance.GetEquipSlotEnchantingCost(slotTypeId);
            var formula =
                FormulaManager.Instance.GetFormula((uint)FormulaKind.EnchantScaleCost);
            if (slotCost == null || formula == null)
                return false;

            var parameters = new Dictionary<string, double>
            {
                ["item_level"] = item.Template.Level,
                ["scale_cost"] = ratio.Cost,
                ["equip_slot_enchant_cost"] = slotCost.Cost,
                ["enchant_scale_cost_mul"] =
                    character.GetEnchantScaleCostMultiplier()
            };
            var value = formula.Evaluate(parameters);
            if (double.IsNaN(value) || double.IsInfinity(value) ||
                value < 0 || value > int.MaxValue)
                return false;

            // x2game FUN_39868400 rounds a positive result with +0.5 then
            // truncates to the integer currency amount.
            cost = (int)(value + 0.5d);
            return true;
        }

        private static bool TryGetSlotTypeId(
            ItemTemplate template,
            out uint slotTypeId)
        {
            switch (template)
            {
                case WeaponTemplate weapon when weapon.HoldableTemplate != null:
                    slotTypeId = weapon.HoldableTemplate.SlotTypeId;
                    return true;
                case ArmorTemplate armor when armor.SlotTemplate != null:
                    slotTypeId = armor.SlotTemplate.SlotTypeId;
                    return true;
                default:
                    slotTypeId = 0;
                    return false;
            }
        }

        private static void Reject(Character character, Skill skill, string reason)
        {
            character.SendMessage($"[Temper8] {reason}");
            Cancel(skill);
        }

        private static void Cancel(Skill skill)
        {
            if (skill != null)
                skill.Cancelled = true;
        }
    }
}
