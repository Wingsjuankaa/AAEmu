using System;
using System.Collections.Generic;

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
    /// <summary>
    /// Native Kakao 8.0 item-change-mapping/awakening transaction.
    /// </summary>
    public class ItemAwakening : SpecialEffectAction
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
                casterObj is not SkillItem reactiveCaster ||
                targetObj is not SkillCastItemTarget itemTarget)
            {
                Reject(
                    caster as Character,
                    skill,
                    "The native AA8 awakening context is incomplete.");
                return;
            }

            var reactive =
                owner.Inventory.GetItemById(reactiveCaster.ItemId);
            var targetItem =
                owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            var preview = ItemAwakeningService.Instance.CreatePreview(
                targetItem,
                reactive,
                checked((uint)value1),
                skill?.Template?.Id ?? 0);
            if (!preview.IsValid)
            {
                Reject(owner, skill, preview.FailureReason);
                return;
            }
            if (targetItem.HasFlag(ItemFlag.EnchantDisabled))
            {
                Reject(
                    owner,
                    skill,
                    "The native AA8 item is crystallized and must be restored " +
                    "before awakening.");
                return;
            }
            if (!HasReactiveCount(
                    reactive,
                    preview.Reactive.ConsumeCount))
            {
                Reject(
                    owner,
                    skill,
                    "The awakening scroll count changed before completion.");
                return;
            }

            AwakeningTransactionPlan transaction;
            try
            {
                transaction =
                    ItemAwakeningService.Instance.CreateTransactionPlan(
                        preview,
                        Rand.Next(0, 10000),
                        Rand.Next(0, 10000),
                        EvolutionTestModeManager.Instance.Get(owner),
                        maximum => Rand.Next(0, maximum));
            }
            catch (InvalidOperationException exception)
            {
                Reject(owner, skill, exception.Message);
                return;
            }

            var before =
                ItemEvolutionStateService.Instance.CreateSnapshot(targetItem);
            var tasks = new List<ItemTask>();
            if (!TryConsumeReactive(
                    owner,
                    reactive,
                    preview.Reactive.ConsumeCount,
                    tasks))
            {
                Reject(
                    owner,
                    skill,
                    "The awakening scroll changed before the atomic mutation.");
                return;
            }
            skill.SkipAutomaticItemConsumption = true;

            if (transaction.Success)
            {
                var targetTemplate = ItemManager.Instance.GetTemplate(
                    preview.Mapping.TargetItemId);
                targetItem.TemplateId = targetTemplate.Id;
                targetItem.Template = targetTemplate;
                targetItem.Grade =
                    checked((byte)preview.TargetGradeId);
                targetItem.EvolutionExperience =
                    preview.MappingGroup.EvolvingExpInherit
                        ? before.EvolutionExperience
                        : 0;
                targetItem.MappingFailBonus = 0;
                targetItem.RemoveFlag(ItemFlag.EnchantDisabled);
                ItemEvolutionStateService.Instance.WriteRandomModifierIds(
                    targetItem,
                    transaction.AfterModifierIds);
            }
            else
            {
                targetItem.MappingFailBonus =
                    transaction.AfterFailBonus;
                if (transaction.Crystallized)
                    targetItem.SetFlag(ItemFlag.EnchantDisabled);
            }
            targetItem.IsDirty = true;

            tasks.Add(new ItemUpdate(targetItem));
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.Evolving,
                tasks,
                new List<ulong>()));
            owner.SendPacket(new SCItemChangeMappingResultPacket(
                before,
                targetItem,
                transaction.Result,
                preview.MappingGroup.Id));

            if (targetItem.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            _log.Info(
                "AA8 awakening: character={0}, item={1}, before={2}/g{3}, " +
                "after={4}/g{5}, group={6}, scroll={7}x{8}, result={9}, " +
                "successBp={10}, disableBp={11}, failBonus={12}->{13}",
                owner.Name,
                targetItem.Id,
                before.TemplateId,
                before.Grade,
                targetItem.TemplateId,
                targetItem.Grade,
                preview.MappingGroup.Id,
                reactive.TemplateId,
                preview.Reactive.ConsumeCount,
                transaction.Result,
                preview.EffectiveSuccessBasisPoints,
                preview.CrystallizationBasisPoints,
                before.MappingFailBonus,
                targetItem.MappingFailBonus);
        }

        private static bool HasReactiveCount(Item reactive, int amount)
        {
            return reactive?._holdingContainer != null &&
                   amount > 0 &&
                   reactive._holdingContainer.GetAllItemsByTemplate(
                       reactive.TemplateId,
                       -1,
                       out _,
                       out var available) &&
                   available >= amount;
        }

        private static bool TryConsumeReactive(
            Character owner,
            Item preferred,
            int amount,
            ICollection<ItemTask> tasks)
        {
            var container = preferred?._holdingContainer;
            if (owner == null ||
                container == null ||
                amount <= 0 ||
                !container.GetAllItemsByTemplate(
                    preferred.TemplateId,
                    -1,
                    out var matching,
                    out var available) ||
                available < amount ||
                !matching.Remove(preferred))
                return false;

            matching.Insert(0, preferred);
            var remaining = amount;
            foreach (var item in matching)
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
                    var remove = new ItemRemove(item);
                    if (!container.RemoveItem(
                            ItemTaskType.Invalid,
                            item,
                            true))
                        return false;
                    tasks.Add(remove);
                }
                remaining -= consumed;
            }
            container.UpdateFreeSlotCount();
            return remaining == 0;
        }

        private static void Reject(
            Character owner,
            Skill skill,
            string reason)
        {
            owner?.SendMessage("[Evolution8] {0}", reason);
            if (skill == null)
                return;
            skill.Cancelled = true;
            owner?.BroadcastPacket(new SCSkillEndedPacket(), true);
        }
    }
}
