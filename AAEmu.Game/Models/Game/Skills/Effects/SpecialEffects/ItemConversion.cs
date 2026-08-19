using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>AA10 item conversion (special effect 49), including the Transmuter repackage flow.</summary>
public class ItemConversion : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemConversion;

    public override void Execute(
        BaseUnit caster,
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
        // This effect commits the exact source stack together with the selected target. Generic skill
        // cleanup must not consume a second Transmuter after the conversion has completed or failed.
        if (skill is not null)
            skill.SkipAutomaticItemConsumption = true;

        if (caster is not Character owner ||
            casterObj is not SkillItem itemCaster ||
            targetObj is not SkillCastItemTarget itemTarget ||
            skill?.Template is null || value1 <= 0)
        {
            Reject(owner: caster as Character, skill, "The item-conversion cast context is incomplete.");
            return;
        }

        var bag = owner.Inventory.Bag;
        var sourceItem = owner.Inventory.GetItemById(itemCaster.ItemId);
        var targetItem = owner.Inventory.GetItemById(itemTarget.Id);
        if (sourceItem is null || targetItem is null || ReferenceEquals(sourceItem, targetItem) ||
            !ReferenceEquals(sourceItem._holdingContainer, bag) ||
            !ReferenceEquals(targetItem._holdingContainer, bag) ||
            sourceItem.Count < 1 || targetItem.Count < 1 ||
            sourceItem.TemplateId != itemCaster.ItemTemplateId ||
            sourceItem.Template?.UseSkillId != skill.Template.Id)
        {
            Reject(owner, skill, "The selected source or conversion target is stale or outside the backpack.",
                ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        if (!targetItem.Template.Disenchantable)
        {
            Reject(owner, skill, $"Target item {targetItem.TemplateId} is not convertible.");
            return;
        }

        var resolution = ItemConversionGameData.Instance.Resolve(
            value1,
            targetItem.Grade,
            targetItem.Template.ImplId,
            targetItem.TemplateId,
            targetItem.Template.Level);
        if (!resolution.IsValid)
        {
            Reject(owner, skill, resolution.FailureReason);
            return;
        }

        var laborCost = skill.CalculateLaborCost(owner);
        if (laborCost < 0 || laborCost > short.MaxValue ||
            owner.LaborPower + owner.LocalLaborPower < laborCost)
        {
            Reject(owner, skill, $"Item conversion needs {laborCost} labor.",
                ErrorMessageType.NotEnoughLaborPower);
            return;
        }

        // A product grade of -1 means that the conversion inherits the source grade. Fixed-grade
        // output templates still normalize to their catalogue grade inside ItemContainer.
        var rewards = resolution.Rewards
            .Select(reward => (
                TemplateId: reward.ItemId,
                reward.Amount,
                Grade: reward.GradeId < 0 ? targetItem.Grade : reward.GradeId))
            .ToArray();
        var tasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var forceRemove = new List<ulong>();

        lock (bag.Items)
        {
            // Both exact selected stacks can release a slot in the same atomic mutation.
            var freedSlots = (sourceItem.Count == 1 ? 1 : 0) + (targetItem.Count == 1 ? 1 : 0);
            if (!bag.CanAcquireDefaultItems(rewards, freedSlots))
            {
                Reject(owner, skill, "The backpack cannot hold all item-conversion products.",
                    ErrorMessageType.BagFull);
                return;
            }

            if (!bag.TryConsumeExactItemsIntoTaskBatch(
                    [(sourceItem, 1), (targetItem, 1)], tasks, forceRemove))
            {
                Reject(owner, skill, "The exact conversion items changed before commit.",
                    ErrorMessageType.NotEnoughRequiredItem);
                return;
            }

            // Templates and capacity were preflighted under the same re-entrant container lock.
            if (!bag.TryAcquireDefaultItemsIntoTaskBatch(rewards, rewardTasks))
                throw new InvalidOperationException(
                    "A preflighted AA10 item-conversion reward could not be acquired.");
        }

        foreach (var packet in ItemContainer.BuildIndependentItemTaskPackets(
                     ItemTaskType.Conversion, tasks, forceRemove))
            owner.SendPacket(packet);

        // r575 does not reliably apply multiple variable-sized Take bodies in one packet. Keep each
        // reward on its own packet boundary while the server-side mutation remains atomic.
        foreach (var rewardTask in rewardTasks)
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.Conversion, rewardTask, []));

        Logger.Info(
            "AA10 item conversion: character={0}, source={1}/{2}, target={3}/{4}, set={5}, route={6}, " +
            "products={7}, labor={8}",
            owner.Name,
            sourceItem.Id,
            sourceItem.TemplateId,
            targetItem.Id,
            targetItem.TemplateId,
            value1,
            resolution.Route.Id,
            string.Join(",", rewards.Select(reward =>
                $"{reward.TemplateId}x{reward.Amount}@{reward.Grade}")),
            laborCost);
    }

    private static void Reject(
        Character owner,
        Skill skill,
        string reason,
        ErrorMessageType error = ErrorMessageType.Invalid)
    {
        if (skill is not null)
        {
            skill.SkipAutomaticItemConsumption = true;
            skill.Cancelled = true;
        }

        if (owner is not null && error != ErrorMessageType.Invalid)
            owner.SendErrorMessage(error);
        Logger.Warn("Rejected AA10 item conversion for character {0}: {1}", owner?.Id ?? 0, reason);
    }
}
