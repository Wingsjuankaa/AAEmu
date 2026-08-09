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
                casterObj is not SkillCasterUnit unitCaster ||
                unitCaster.ObjId != owner.ObjId ||
                targetObj is not SkillCastItemTarget itemTarget ||
                skillObject is not SkillObjectEvolvingMaterials materialOptions ||
                !materialOptions.TryGetMaterialItemIds(
                    out var selectedMaterialIds))
            {
                Reject(
                    caster as Character,
                    skill,
                    "The native AA8 synthesis context is incomplete.");
                return;
            }

            var targetItem =
                owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            var materials = new List<SynthesisMaterialSelection>(
                selectedMaterialIds.Count);
            var uniqueMaterialIds = new HashSet<ulong>();
            foreach (var materialId in selectedMaterialIds)
            {
                if (!uniqueMaterialIds.Add(materialId))
                {
                    Reject(
                        owner,
                        skill,
                        "The native AA8 synthesis material list contains a duplicate item.");
                    return;
                }
                materials.Add(new SynthesisMaterialSelection
                {
                    Item = owner.Inventory.GetItemById(materialId),
                    Count = 1
                });
            }

            var preview = ItemSynthesisService.Instance.CreatePreview(
                targetItem,
                materials,
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
            if (!TryConsumeMaterialsIntoTransaction(
                    owner,
                    materials,
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
            // "evolving". Grade is outside the AA8 detail union, so a grade
            // transition requires ChangeGrade before UpdateDetail. Mode-7
            // then rebuilds the Gear Upgrade target and result dialog.
            tasks.AddRange(
                ItemEvolutionTaskBuilder.CreateGradeAndDetailUpdate(
                    targetItem,
                    checked((byte)preview.BeforeGradeId),
                    checked((byte)transaction.AfterGradeId)));
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
                "AA8 synthesis applied: character={0}, target={1}/{2}, materials={3}, exp={4}+{5}, grade={6}->{7}, sectionExp={8}->{9}, cost={10}",
                owner.Name,
                targetItem.Id,
                targetItem.TemplateId,
                string.Join(
                    ",",
                    materials.Select(selection =>
                        $"{selection.Item.Id}/{selection.Item.TemplateId}")),
                preview.MaterialExperience,
                transaction.BonusExperience,
                preview.BeforeGradeId,
                transaction.AfterGradeId,
                preview.BeforeSectionExperience,
                transaction.AfterSectionExperience,
                preview.GoldCost);
        }

        private static bool TryConsumeMaterialsIntoTransaction(
            Character owner,
            IReadOnlyList<SynthesisMaterialSelection> materials,
            ICollection<ItemTask> tasks)
        {
            if (owner == null ||
                materials == null ||
                materials.Count == 0)
                return false;

            foreach (var selection in materials)
            {
                var item = selection?.Item;
                if (item == null ||
                    selection.Count <= 0 ||
                    item.Count < selection.Count ||
                    item._holdingContainer == null ||
                    !item._holdingContainer.Items.Contains(item) ||
                    owner.Inventory.GetItemById(item.Id) != item)
                    return false;
            }

            var touchedContainers = new HashSet<ItemContainer>();
            foreach (var selection in materials)
            {
                var item = selection.Item;
                var container = item._holdingContainer;
                var consumed = selection.Count;
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
                touchedContainers.Add(container);
            }

            foreach (var container in touchedContainers)
                container.UpdateFreeSlotCount();
            return true;
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
            owner?.BroadcastPacket(new SCSkillEndedPacket(skill.TlId), true);
        }
    }
}
