using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Core.Managers;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class ItemSocketing : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemSocketing;

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
        // TODO ...
        Logger.Debug("Special effects: ItemSocketing value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4);

        if (caster is not Character owner)
        {
            Logger.Error($"Special effects: ItemSocketing caster {caster.Id} is not a character");
            return;
        }

        if (casterObj is not SkillItem gemSkillItem)
        {
            Logger.Error($"Special effects: ItemSocketing casterObj {casterObj} is not a SkillItem");
            return;
        }

        if (targetObj is not SkillCastItemTarget skillTargetItem)
        {
            Logger.Error($"Special effects: ItemSocketing targetObj {targetObj} is not a SkillCastItemTarget");
            return;
        }

        var targetItem = owner.Inventory.GetItemById(skillTargetItem.Id);
        var gemItem = owner.Inventory.GetItemById(gemSkillItem.ItemId);

        if (targetItem is null || gemItem is null)
        {
            Logger.Warn($"Special effects: ItemSocketing targetItem {skillTargetItem.Id} or gemItem {gemSkillItem.ItemId} not found");
            return;
        }

        if (targetItem is not EquipItem equipItem)
        {
            Logger.Warn($"Special effects: ItemSocketing targetItem {skillTargetItem.Id} was not a EquipItem");
            return;
        }

        var tasksSocketing = new List<ItemTask>();

        byte result = 0;
        var installed = false;
        if (gemItem.TemplateId != Item.DawnStone)
        {
            // Add LunaGem
            var gemCount = 0u;
            foreach (var gem in equipItem.GemIds)
            {
                if (gem != 0)
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

            // Roll for Success
            var gemRoll = Random.Shared.Next(0, 10000);
            var gemChance = ItemManager.Instance.GetSocketChance(gemCount); // fetches chances from sqlite3
            // var gemChance = int.MaxValue; //gives 100% success rates

            if (gemRoll < gemChance)
            {
                // Success
                equipItem.GemIds[gemCount] = gemItem.TemplateId;
                result = 1;
            }

            var socketIndexes = new List<int>(requestedCount);
            for (var index = 0;
                 index < validation.MaximumSockets &&
                 socketIndexes.Count < requestedCount;
                 index++)
            {
                // Failed!
                for (var i = 0; i < equipItem.GemIds.Length; i++)
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
            installed = true;
        }
        else
        {
            // DawnStone
            for (var i = 0; i < equipItem.GemIds.Length; i++)
            {
                equipItem.GemIds[i] = 0;
            }
            result = 1;
        }

        tasksSocketing.Add(new ItemUpdate(equipItem));

        owner.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.Socketing, tasksSocketing, []));
        owner.SendPacket(new SCItemSocketingLunagemResultPacket(result, equipItem.Id, gemItem.TemplateId, installed));
        owner.BroadcastPacket(new SCSkillEndedPacket(skill.TlId), true);
    }
}
