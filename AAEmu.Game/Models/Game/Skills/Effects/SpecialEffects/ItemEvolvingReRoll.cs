using System;
using System.Collections.Generic;

using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemEvolvingReRoll : SpecialEffectAction
    {
        protected virtual bool RequiresExplicitGroup => false;

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
                targetObj is not SkillCastItemTarget itemTarget ||
                skillObject is not SkillObjectEvolvingRerollOptions options)
            {
                Reject(
                    caster as Character,
                    skill,
                    "The native AA8 reroll context is incomplete.");
                return;
            }

            var reactive = owner.Inventory.GetItemById(reactiveCaster.ItemId);
            var targetItem =
                owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            if (reactive?._holdingContainer == null || targetItem == null)
            {
                Reject(owner, skill, "The reroll reagent or target is missing.");
                return;
            }
            if (RequiresExplicitGroup && options.ChangeToGroupId == 0)
            {
                Reject(
                    owner,
                    skill,
                    "The native AA8 selective reroll requires an explicit " +
                    "replacement modifier group.");
                return;
            }

            var profile = ItemEvolutionRuleService.Instance.GetProfile(
                targetItem.TemplateId,
                targetItem.Grade);
            if (profile.Category == null ||
                !ItemEvolutionRuleService.Instance.IsRerollItem(
                    profile.Category.ReRollItemSetId,
                    reactive.TemplateId))
            {
                Reject(
                    owner,
                    skill,
                    "The reagent does not belong to the target's native AA8 " +
                    "reroll item set.");
                return;
            }

            var modifierIndex = checked((int)options.ModifierIndex);
            var reroll = ItemRandomAttributeService.Instance.ResolveReroll(
                targetItem,
                modifierIndex,
                options.ChangeToGroupId,
                maximum => Rand.Next(0, maximum));
            if (!reroll.IsValid)
            {
                Reject(owner, skill, reroll.FailureReason);
                return;
            }

            var tasks = new List<ItemTask>();
            owner.Inventory.OnConsumedItem(reactive, 1);
            if (reactive.Count > 1)
            {
                reactive.Count--;
                tasks.Add(new ItemCountUpdate(reactive, -1));
            }
            else
            {
                var remove = new ItemRemove(reactive);
                if (!reactive._holdingContainer.RemoveItem(
                        ItemTaskType.Invalid,
                        reactive,
                        true))
                {
                    Reject(
                        owner,
                        skill,
                        "The reroll reagent changed before completion.");
                    return;
                }
                tasks.Add(remove);
            }
            skill.SkipAutomaticItemConsumption = true;

            targetItem.SetNativeRandomModifierId(
                modifierIndex,
                reroll.AfterModifierId);
            targetItem.IsDirty = true;
            tasks.Add(new ItemUpdate(targetItem));
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.Evolving,
                tasks,
                new List<ulong>()));
            owner.SendPacket(new SCEvolvingReRollResultPacket(
                targetItem.Id,
                checked((byte)modifierIndex),
                true,
                ToPacketModifier(reroll.Before),
                ToPacketModifier(reroll.After)));

            if (targetItem.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            _log.Info(
                "AA8 evolving reroll: character={0}, item={1}/{2}, " +
                "index={3}, modifier={4}->{5}, requestedGroup={6}, reagent={7}",
                owner.Name,
                targetItem.Id,
                targetItem.TemplateId,
                modifierIndex,
                reroll.BeforeModifierId,
                reroll.AfterModifierId,
                options.ChangeToGroupId,
                reactive.TemplateId);
        }

        private static EvolvingModifierResult ToPacketModifier(
            ItemRandomAttributeValue value)
        {
            return new EvolvingModifierResult
            {
                UnitAttributeId = value.UnitAttributeId,
                UnitModifierTypeId = value.UnitModifierTypeId,
                Value = value.Value
            };
        }

        private static void Reject(Character owner, Skill skill, string reason)
        {
            owner?.SendMessage("[Evolution8] {0}", reason);
            if (skill == null)
                return;
            skill.Cancelled = true;
            owner?.BroadcastPacket(new SCSkillEndedPacket(), true);
        }
    }
}
