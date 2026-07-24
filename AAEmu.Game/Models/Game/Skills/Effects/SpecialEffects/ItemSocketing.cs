using System;

using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
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

            // The AA8 client in this build did not expose socket0..socket9 for
            // its active chance sets, nor have cost/failure side effects been
            // provenance-locked yet. Keep the validated request immutable
            // until those native inputs are available.
            _log.Warn(
                "AA8 socket request validated but mutation is gated: target={0}, reagent={1}, chance={2}",
                targetItem.Id,
                reagent.TemplateId,
                validation.SuccessChance);
            owner.SendMessage(
                "[Socket8] The item is compatible, but native AA8 cost/failure execution is not active yet.");
            owner.SendPacket(new SCSocketingResultPacket(
                0, targetItem.Id, reagent.TemplateId, 1, false));
            EndSkill(owner, skill);
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
            if (owner != null && skill != null)
                owner.BroadcastPacket(new SCSkillEndedPacket(skill.TlId), true);
        }
    }
}
