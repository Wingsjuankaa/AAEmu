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
            _log.Trace(
                "AA8 socket request: value1={0}, value2={1}, value3={2}, value4={3}",
                value1, value2, value3, value4);

            var owner = caster as Character;
            if (owner == null ||
                casterObj is not SkillItem reagentCaster ||
                targetObj is not SkillCastItemTarget itemTarget)
            {
                EndSkill(owner, skill);
                return;
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
                EndSkill(owner, skill);
                return;
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
                EndSkill(owner, skill);
                return;
            }

            if (!ItemSocketRuleService.Instance.TryCalculateCost(
                    owner,
                    targetItem,
                    reagent,
                    validation,
                    out var cost))
            {
                Reject(owner, skill, targetItem, reagent,
                    "The native AA8 socketing cost could not be resolved.");
                return;
            }

            if (owner.Money < cost)
            {
                owner.SendErrorMessage(ErrorMessageType.NotEnoughMoney);
                EndSkill(owner, skill);
                return;
            }

            if (!targetItem.TryGetFirstEmptyNativeSocket(
                    validation.MaximumSockets,
                    out var gemArrayIndex))
            {
                owner.SendErrorMessage(ErrorMessageType.ItemSocketsFull);
                EndSkill(owner, skill);
                return;
            }

            if (!owner.SubtractMoney(
                    SlotType.Inventory,
                    cost,
                    ItemTaskType.Socketing))
            {
                EndSkill(owner, skill);
                return;
            }

            var socketIndex = gemArrayIndex - EquipItem.NativeSocketStartIndex;
            if (!targetItem.SetNativeSocket(socketIndex, reagent.TemplateId))
            {
                owner.AddMoney(SlotType.Inventory, cost, ItemTaskType.Socketing);
                Reject(owner, skill, targetItem, reagent,
                    "The target socket changed during execution.");
                return;
            }

            owner.SendPacket(
                new SCItemTaskSuccessPacket(
                    ItemTaskType.Socketing,
                    new ItemUpdate(targetItem),
                    new List<ulong>()));

            if (targetItem.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            owner.SendPacket(new SCSocketingResultPacket(
                0, targetItem.Id, reagent.TemplateId, 1, true));
            _log.Info(
                "AA8 guaranteed socket installed: character={0}, target={1}/{2}, reagent={3}, socket={4}, cost={5}, evidence={6}",
                owner.Name,
                targetItem.Id,
                targetItem.TemplateId,
                reagent.TemplateId,
                socketIndex,
                cost,
                validation.Definition.GuaranteeEvidence);
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
            string reason)
        {
            owner.SendMessage("[Socket8] {0}", reason);
            owner.SendPacket(new SCSocketingResultPacket(
                0,
                targetItem?.Id ?? 0,
                reagent?.TemplateId ?? 0,
                1,
                false));
            EndSkill(owner, skill);
        }
    }
}
