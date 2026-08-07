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
    /// <summary>
    /// Native AA8 decrystallization path:
    /// item 45732 -> skill 39040 -> effect 70715 ->
    /// SpecialEffect 35710/type 156.
    /// </summary>
    public sealed class RestoreDisableEnchant : SpecialEffectAction
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
                    "The native AA8 decrystallization context is incomplete.");
                return;
            }

            var reactive = owner.Inventory.GetItemById(reactiveCaster.ItemId);
            var equipment =
                owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            if (reactive?._holdingContainer == null || equipment == null)
            {
                Reject(
                    owner,
                    skill,
                    "The decrystallization scroll or target is missing.");
                return;
            }
            if (reactive.TemplateId != reactiveCaster.ItemTemplateId ||
                reactive.Template?.UseSkillId != skill?.Template?.Id)
            {
                Reject(
                    owner,
                    skill,
                    "The decrystallization scroll and native AA8 skill do not match.");
                return;
            }
            if (!equipment.HasFlag(ItemFlag.EnchantDisabled))
            {
                Reject(
                    owner,
                    skill,
                    "The selected item is not crystallized.");
                return;
            }

            // The AA8 scroll explicitly excludes crafted equipment. Within
            // B13 only equipment in the native Hiram awakening graph is
            // enabled, which gives a structural validation without guessing
            // from localized names or historical item lists.
            var evolution = ItemEvolutionRuleService.Instance.GetProfile(
                equipment.TemplateId,
                equipment.Grade);
            if (!evolution.HasAwakeningDefinition)
            {
                Reject(
                    owner,
                    skill,
                    "The target has no enabled native AA8 awakening mapping.");
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
                var removal = new ItemRemove(reactive);
                if (!reactive._holdingContainer.RemoveItem(
                        ItemTaskType.Invalid,
                        reactive,
                        true))
                {
                    Reject(
                        owner,
                        skill,
                        "The scroll changed before the atomic mutation.");
                    return;
                }
                tasks.Add(removal);
            }
            skill.SkipAutomaticItemConsumption = true;

            equipment.RemoveFlag(ItemFlag.EnchantDisabled);
            equipment.IsDirty = true;
            tasks.Add(new ItemUpdate(equipment));
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.RestoreDisableEnchant,
                tasks,
                new List<ulong>()));

            if (equipment.SlotType == SlotType.Equipment)
            {
                owner.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(owner);
            }

            _log.Info(
                "AA8 decrystallization: character={0}, item={1}/{2}, " +
                "scroll={3}, task=170",
                owner.Name,
                equipment.Id,
                equipment.TemplateId,
                reactive.TemplateId);
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
            owner?.BroadcastPacket(new SCSkillEndedPacket(skill.TlId), true);
        }
    }
}
