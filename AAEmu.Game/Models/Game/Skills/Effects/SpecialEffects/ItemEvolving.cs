using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemEvolving : SpecialEffectAction
    {
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
            if (caster is not Character owner ||
                casterObj is not SkillItem materialCaster ||
                targetObj is not SkillCastItemTarget itemTarget)
            {
                Reject(
                    caster as Character,
                    skill,
                    "The native AA8 synthesis context is incomplete.");
                return;
            }

            var material = owner.Inventory.GetItemById(materialCaster.ItemId);
            var targetItem =
                owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            var requestedCount = materialCaster.Type2 == 0
                ? 1
                : materialCaster.Type2 > int.MaxValue
                    ? int.MaxValue
                    : (int)materialCaster.Type2;
            var preview = ItemSynthesisService.Instance.CreatePreview(
                targetItem,
                new List<SynthesisMaterialSelection>
                {
                    new() { Item = material, Count = requestedCount }
                },
                skill?.Template?.ConsumeLaborPower ?? 0);
            if (!preview.IsValid)
            {
                Reject(owner, skill, preview.FailureReason);
                return;
            }
            if (owner.Money < preview.GoldCost)
            {
                owner.SendErrorMessage(ErrorMessageType.NotEnoughMoney);
                Reject(
                    owner,
                    skill,
                    "Not enough currency for AA8 synthesis.",
                    false);
                return;
            }

            var bonusMinimum = System.Math.Clamp(
                preview.BonusExperienceMinimum,
                0,
                1000);
            var bonusMaximum = System.Math.Clamp(
                preview.BonusExperienceMaximum,
                bonusMinimum,
                1000);
            var testMode = EvolutionTestModeManager.Instance.Get(owner);
            var transaction = ItemSynthesisService.Instance.CreateTransactionPlan(
                preview,
                Rand.Next(0, 1000),
                testMode == EvolutionTestMode.BonusExperience
                    ? bonusMaximum
                    : Rand.Next(bonusMinimum, bonusMaximum + 1),
                testMode == EvolutionTestMode.BonusExperience);
            var attributes =
                ItemRandomAttributeService.Instance.ResolveForSynthesis(
                    targetItem,
                    transaction.AfterGradeId,
                    transaction.AfterSectionExperience,
                    maximum => Rand.Next(0, maximum));
            if (!attributes.IsValid)
            {
                Reject(owner, skill, attributes.FailureReason);
                return;
            }

            var tasks = new List<ItemTask>();
            if (!TryConsumeMaterialIntoTransaction(
                    owner,
                    material,
                    requestedCount,
                    tasks))
            {
                Reject(
                    owner,
                    skill,
                    "The synthesis material changed before completion.");
                return;
            }
            skill.SkipAutomaticItemConsumption = true;

            owner.Money -= preview.GoldCost;
            tasks.Insert(0, new MoneyChange(-preview.GoldCost));
            ItemEvolutionStateService.Instance.WriteSynthesisState(
                targetItem,
                transaction.AfterGradeId,
                transaction.AfterSectionExperience);
            ItemEvolutionStateService.Instance.WriteRandomModifierIds(
                targetItem,
                attributes.ModifierIds);

            if (targetItem.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            // X2::GameClient::ApplyItemTaskToSelf names reason 100
            // "evolving". Mode-7 consumes UpdateDetail from this transaction
            // before rebuilding the Gear Upgrade target and result dialog.
            tasks.Add(new ItemUpdate(targetItem));
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.Evolving,
                tasks,
                new List<ulong>()));
            owner.SendPacket(new SCEvolvingResultPacket(
                targetItem.Id,
                checked((byte)preview.BeforeGradeId),
                checked((byte)transaction.AfterGradeId),
                checked((int)preview.MaterialExperience),
                checked((int)transaction.BonusExperience),
                0,
                attributes.Values
                    .Where(value => value.Added)
                    .Select(value => new EvolvingModifierResult
                    {
                        UnitAttributeId = value.UnitAttributeId,
                        UnitModifierTypeId = value.UnitModifierTypeId,
                        Value = value.Value
                    })
                    .ToList()));

            _log.Info(
                "AA8 synthesis applied: character={0}, target={1}/{2}, material={3}x{4}, exp={5}+{6}, grade={7}->{8}, sectionExp={9}->{10}, cost={11}",
                owner.Name,
                targetItem.Id,
                targetItem.TemplateId,
                material.TemplateId,
                requestedCount,
                preview.MaterialExperience,
                transaction.BonusExperience,
                preview.BeforeGradeId,
                transaction.AfterGradeId,
                preview.BeforeSectionExperience,
                transaction.AfterSectionExperience,
                preview.GoldCost);
        }

        private static bool TryConsumeMaterialIntoTransaction(
            Character owner,
            Item preferredMaterial,
            int amount,
            ICollection<ItemTask> tasks)
        {
            var container = preferredMaterial?._holdingContainer;
            if (owner == null ||
                container == null ||
                amount <= 0 ||
                !container.GetAllItemsByTemplate(
                    preferredMaterial.TemplateId,
                    -1,
                    out var matchingItems,
                    out var available) ||
                available < amount ||
                !matchingItems.Remove(preferredMaterial))
                return false;

            matchingItems.Insert(0, preferredMaterial);
            var remaining = amount;
            foreach (var item in matchingItems)
            {
                if (remaining <= 0)
                    break;

                var consumed = Math.Min(item.Count, remaining);
                owner.Inventory.OnConsumedItem(item, consumed);
                if (consumed < item.Count)
                {
                    item.Count -= consumed;
                    tasks.Add(new ItemCountUpdate(item, -consumed));
                }
                else
                {
                    var removeTask = new ItemRemove(item);
                    if (!container.RemoveItem(
                            ItemTaskType.Invalid,
                            item,
                            true))
                        return false;
                    tasks.Add(removeTask);
                }
                remaining -= consumed;
            }

            container.UpdateFreeSlotCount();
            return remaining == 0;
        }

        private static void Reject(
            Character owner,
            Skill skill,
            string reason,
            bool cancelSkill = true)
        {
            owner?.SendMessage("[Evolution8] {0}", reason);
            if (!cancelSkill || skill == null)
                return;
            skill.Cancelled = true;
            owner?.BroadcastPacket(new SCSkillEndedPacket(), true);
        }
    }
}
