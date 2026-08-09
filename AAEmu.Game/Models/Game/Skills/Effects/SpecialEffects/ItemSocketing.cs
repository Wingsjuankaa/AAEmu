using System;
using System.Collections.Generic;

using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemSocketing : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ItemSocketing;

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
            ExecuteInstall(
                caster,
                casterObj,
                targetObj,
                skill,
                1,
                false,
                true);
        }

        /// <summary>
        /// Executes the AA8 Gear Upgrade socket context carried by
        /// SkillObject type 10. This is deliberately separate from the
        /// reagent's ordinary right-click effect: for Lunascales skill 37186
        /// grants Honor when used on the character, but installs the socket
        /// when the same skill targets an equipment item with this context.
        /// </summary>
        public bool ExecuteNativeSocketContext(
            Unit caster,
            SkillCaster casterObj,
            SkillCastTarget targetObj,
            Skill skill,
            SkillObjectSocketInstallOptions options)
        {
            var requestedCount = options?.Count ?? 1;
            if (requestedCount == 0)
                requestedCount = 1;
            if (requestedCount > int.MaxValue)
                requestedCount = int.MaxValue;

            return ExecuteInstall(
                caster,
                casterObj,
                targetObj,
                skill,
                (int)requestedCount,
                true,
                false);
        }

        private bool ExecuteInstall(
            Unit caster,
            SkillCaster casterObj,
            SkillCastTarget targetObj,
            Skill skill,
            int requestedCount,
            bool consumeReagent,
            bool endRejectedSkill)
        {
            _log.Trace(
                "AA8 socket request: count={0}, contextual={1}",
                requestedCount,
                consumeReagent);

            var owner = caster as Character;
            if (owner == null ||
                casterObj is not SkillItem reagentCaster ||
                targetObj is not SkillCastItemTarget itemTarget)
            {
                if (endRejectedSkill)
                    EndSkill(owner, skill);
                return false;
            }

            var targetItem = owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            var reagent = owner.Inventory.GetItemById(reagentCaster.ItemId);
            var validation = ItemSocketRuleService.Instance.Validate(targetItem, reagent);
            if (!validation.IsValid)
            {
                _log.Warn(
                    "Blocked AA8 socket request owner={0}, target={1}, reagent={2}: {3} ({4})",
                    owner.Id,
                    targetItem?.Id ?? 0,
                    reagent?.TemplateId ?? 0,
                    validation.Failure,
                    validation.Reason);
                SendValidationFailure(owner, validation);
                if (targetItem != null && reagent != null)
                    owner.SendPacket(new SCSocketingResultPacket(
                        0, targetItem.Id, reagent.TemplateId, 1, false));
                if (endRejectedSkill)
                    EndSkill(owner, skill);
                return false;
            }

            if (!validation.Definition.Guaranteed)
            {
                // Ordinary/refined Lunagem probabilities are private
                // server-side AA8 data. Keep those requests immutable until
                // socket0..socket9 are recovered from a native source.
                _log.Warn(
                    "AA8 probabilistic socket request remains gated: target={0}, reagent={1}, chance={2}",
                    targetItem.Id,
                    reagent.TemplateId,
                    validation.SuccessChance);
                owner.SendMessage(
                    "[Socket8] This probabilistic Lunagem is compatible, but its native AA8 chance table is unavailable.");
                owner.SendPacket(new SCSocketingResultPacket(
                    0, targetItem.Id, reagent.TemplateId, 1, false));
                if (endRejectedSkill)
                    EndSkill(owner, skill);
                return false;
            }

            var availableSockets =
                validation.MaximumSockets - validation.OccupiedSockets;
            var availableReagents =
                owner.Inventory.GetItemsCount(reagent.TemplateId);
            if (requestedCount < 1 ||
                requestedCount > availableSockets ||
                requestedCount > availableReagents)
            {
                Reject(
                    owner,
                    skill,
                    targetItem,
                    reagent,
                    $"Requested {requestedCount} sockets, but only " +
                    $"{availableSockets} slots and {availableReagents} reagents are available.",
                    endRejectedSkill);
                return false;
            }

            long totalCost = 0;
            for (var index = 0; index < requestedCount; index++)
            {
                var operationValidation = new ItemSocketValidationResult
                {
                    Definition = validation.Definition,
                    ChanceDefinition = validation.ChanceDefinition,
                    OccupiedSockets = validation.OccupiedSockets + index,
                    MaximumSockets = validation.MaximumSockets,
                    SuccessChance = validation.SuccessChance
                };
                if (!ItemSocketRuleService.Instance.TryCalculateCost(
                        owner,
                        targetItem,
                        reagent,
                        operationValidation,
                        out var operationCost))
                {
                    Reject(
                        owner,
                        skill,
                        targetItem,
                        reagent,
                        "The native AA8 socketing cost could not be resolved.",
                        endRejectedSkill);
                    return false;
                }

                totalCost += operationCost;
                if (totalCost > int.MaxValue)
                {
                    Reject(
                        owner,
                        skill,
                        targetItem,
                        reagent,
                        "The native AA8 socketing cost exceeds the supported currency range.",
                        endRejectedSkill);
                    return false;
                }
            }

            if (owner.Money < totalCost)
            {
                owner.SendErrorMessage(ErrorMessageType.NotEnoughMoney);
                if (endRejectedSkill)
                    EndSkill(owner, skill);
                return false;
            }

            var socketIndexes = new List<int>(requestedCount);
            for (var index = 0;
                 index < validation.MaximumSockets &&
                 socketIndexes.Count < requestedCount;
                 index++)
            {
                if (targetItem.GemIds[
                        EquipItem.NativeSocketStartIndex + index] == 0)
                    socketIndexes.Add(index);
            }
            if (socketIndexes.Count != requestedCount)
            {
                owner.SendErrorMessage(ErrorMessageType.ItemSocketsFull);
                if (endRejectedSkill)
                    EndSkill(owner, skill);
                return false;
            }

            // AA8 treats the socket operation as one ItemTask transaction.
            // Sending money, reagent and target updates as three independent
            // Socketing transactions makes X2ItemEnchant refresh its cached
            // target after the first (money-only) update and leaves the Gear
            // Upgrade window one socket behind until it is reopened.
            var socketTasks = new List<ItemTask>
            {
                new MoneyChange(-totalCost)
            };
            owner.Money -= totalCost;

            foreach (var socketIndex in socketIndexes)
            {
                if (targetItem.SetNativeSocket(socketIndex, reagent.TemplateId))
                    continue;

                foreach (var rollbackIndex in socketIndexes)
                    targetItem.SetNativeSocket(rollbackIndex, 0);
                owner.Money += totalCost;
                Reject(
                    owner,
                    skill,
                    targetItem,
                    reagent,
                    "The target socket changed during execution.",
                    endRejectedSkill);
                return false;
            }

            if (consumeReagent)
            {
                if (!TryConsumeReagentIntoTransaction(
                        owner,
                        reagent,
                        requestedCount,
                        socketTasks))
                {
                    foreach (var socketIndex in socketIndexes)
                        targetItem.SetNativeSocket(socketIndex, 0);
                    owner.Money += totalCost;
                    Reject(
                        owner,
                        skill,
                        targetItem,
                        reagent,
                        "The AA8 socket reagent could not be consumed atomically.",
                        endRejectedSkill);
                    return false;
                }
            }

            if (targetItem.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            // FUN_39a56560 applies ItemAction.UpdateDetail synchronously to
            // the client's live item before the socket result (event 0x5A)
            // asks X2ItemEnchant to rebuild the selected target.
            socketTasks.Add(new ItemUpdate(targetItem));
            owner.SendPacket(
                new SCItemTaskSuccessPacket(
                    ItemTaskType.Socketing,
                    socketTasks,
                    new List<ulong>()));
            owner.SendPacket(new SCSocketingResultPacket(
                1, targetItem.Id, reagent.TemplateId, 1, true));
            _log.Info(
                "AA8 guaranteed socket installed: character={0}, target={1}/{2}, reagent={3}, socket={4}, cost={5}, evidence={6}",
                owner.Name,
                targetItem.Id,
                targetItem.TemplateId,
                reagent.TemplateId,
                string.Join(",", socketIndexes),
                totalCost,
                validation.Definition.GuaranteeEvidence);
            return true;
        }

        private static bool TryConsumeReagentIntoTransaction(
            Character owner,
            Item preferredReagent,
            int amount,
            ICollection<ItemTask> tasks)
        {
            var container = preferredReagent?._holdingContainer;
            if (owner == null ||
                container == null ||
                amount <= 0 ||
                !container.GetAllItemsByTemplate(
                    preferredReagent.TemplateId,
                    -1,
                    out var matchingItems,
                    out var available) ||
                available < amount ||
                !matchingItems.Remove(preferredReagent))
                return false;

            matchingItems.Insert(0, preferredReagent);
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
                    // Capture the physical slot before RemoveItem releases the
                    // instance id and detaches it from its container.
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

        private static void SendValidationFailure(
            Character owner,
            ItemSocketValidationResult validation)
        {
            switch (validation.Failure)
            {
                case ItemSocketValidationFailure.SocketsFull:
                    owner.SendErrorMessage(ErrorMessageType.ItemSocketsFull);
                    break;
                case ItemSocketValidationFailure.ItemLevelTooLow:
                    owner.SendErrorMessage(ErrorMessageType.SocketTargetLevel);
                    break;
                default:
                    owner.SendMessage("[Socket8] {0}", validation.Reason);
                    break;
            }
        }

        private static void EndSkill(Character owner, Skill skill)
        {
            if (skill == null)
                return;

            // Skill.ScheduleEffects consumes use_skill_as_reagent items only
            // when the cast is not cancelled. Every path that reaches this
            // helper is a rejected or deliberately gated AA8 socket attempt.
            skill.Cancelled = true;
            if (owner != null)
                owner.BroadcastPacket(new SCSkillEndedPacket(skill.TlId), true);
        }

        private static void Reject(
            Character owner,
            Skill skill,
            EquipItem targetItem,
            Item reagent,
            string reason,
            bool endSkill = true)
        {
            owner.SendMessage("[Socket8] {0}", reason);
            owner.SendPacket(new SCSocketingResultPacket(
                0,
                targetItem?.Id ?? 0,
                reagent?.TemplateId ?? 0,
                1,
                false));
            if (endSkill)
                EndSkill(owner, skill);
        }
    }
}
