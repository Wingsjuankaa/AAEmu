using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Skills;

using NLog;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>
/// Executes the controller-driven AA10 smelting operation carried by skill-object type 20. This is
/// deliberately separate from historical special-effect 151, which is attached to unrelated skills
/// in the r575 catalogue.
/// </summary>
public static class ItemSmeltingService
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    internal static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.itemSmelting);

    public static bool Execute(
        Character owner,
        SkillCaster casterObject,
        SkillCastTarget targetObject,
        Skill skill,
        SkillObjectItemSmeltingOptions options)
    {
        if (skill is not null)
            skill.SkipAutomaticItemConsumption = true;

        if (owner is null || skill?.Template is null || options is null ||
            !IsFeatureEnabled(FeaturesManager.Fsets) ||
            casterObject is not SkillItem catalystCaster ||
            targetObject is not SkillCastItemTarget targetCaster)
            return Reject(owner, skill, "Smelting is disabled or its cast context is incomplete.");

        var definition = ItemManager.Instance.GetItemSmelting(options.SmeltingDescriptionId);
        var probability = definition?.Probability;
        var itemSet = definition is null ? null : ItemManager.Instance.GetItemSet(definition.ItemSetId);
        if (definition is null || probability is null || itemSet is null ||
            definition.Outputs.Count != 3 || definition.Amount <= 0 || definition.Gold < 0 ||
            definition.Outputs.Any(output => ItemManager.Instance.GetTemplate(output.ItemId) is null) ||
            probability.GreatSuccess + probability.Success + probability.Failure !=
            ItemSmeltingCalculator.ProbabilityBase ||
            definition.SkillId != skill.Template.Id)
            return Reject(owner, skill,
                $"Smelting recipe {options.SmeltingDescriptionId} is unavailable or does not belong to skill {skill.Template.Id}.");

        var bag = owner.Inventory.Bag;
        var catalyst = owner.Inventory.GetItemById(catalystCaster.ItemId);
        var target = owner.Inventory.GetItemById(targetCaster.Id);
        if (catalyst is null || target is null || ReferenceEquals(catalyst, target) ||
            !ReferenceEquals(catalyst._holdingContainer, bag) ||
            !ReferenceEquals(target._holdingContainer, bag) ||
            catalyst.TemplateId != catalystCaster.ItemTemplateId ||
            catalyst.Template?.UseSkillId != definition.SkillId || catalyst.Count < 1 ||
            target.TemplateId != definition.ItemId || target.Count < definition.Amount)
            return Reject(owner, skill, "The selected smelting catalyst or target is stale or invalid.",
                ErrorMessageType.NotEnoughRequiredItem);

        if (skill.Template.ActabilityGroupId > 0 &&
            owner.Actability.GetPoint((uint)skill.Template.ActabilityGroupId, true) < definition.ActabilityLimit)
            return Reject(owner, skill,
                $"Smelting recipe {definition.Id} needs {definition.ActabilityLimit} actability.",
                ErrorMessageType.ActabilityNotEnoughPoint);

        var laborCost = skill.CalculateLaborCost(owner);
        if (laborCost < 0 || laborCost > short.MaxValue ||
            owner.LaborPower + owner.LocalLaborPower < laborCost)
            return Reject(owner, skill, $"Smelting recipe {definition.Id} needs {laborCost} labor.",
                ErrorMessageType.NotEnoughLaborPower);

        var materials = itemSet.Items.Values
            .Select(item => (TemplateId: item.ItemId, Amount: item.Count))
            .ToArray();
        if (materials.Length == 0 || materials.Any(item =>
                item.TemplateId == definition.ItemId || item.TemplateId == catalyst.TemplateId))
            return Reject(owner, skill,
                $"Smelting recipe {definition.Id} has an empty or overlapping material set.");

        var outcome = ItemSmeltingCalculator.Resolve(
            definition, Random.Shared.Next(ItemSmeltingCalculator.ProbabilityBase));
        var outputTemplate = ItemManager.Instance.GetTemplate(outcome.Output.ItemId);
        var outputGrade = outputTemplate.FixedGrade >= 0 && !outputTemplate.Gradable
            ? outputTemplate.FixedGrade
            : outcome.Output.GradeId;

        var consumeTasks = new List<ItemTask>();
        var rewardTasks = new List<ItemTask>();
        var forceRemove = new List<ulong>();
        Item resultItem;

        lock (bag.Items)
        {
            if (!CanConsumeTemplates(bag.Items, materials, out var materialFreedSlots))
                return Reject(owner, skill, $"Smelting recipe {definition.Id} is missing materials.",
                    ErrorMessageType.NotEnoughRequiredItem);

            var freedSlots = materialFreedSlots +
                             (target.Count == definition.Amount ? 1 : 0) +
                             (catalyst.Count == 1 ? 1 : 0);
            var rewards = new[]
            {
                (TemplateId: outcome.Output.ItemId, Amount: 1, Grade: outputGrade)
            };
            if (!bag.CanAcquireDefaultItems(rewards, freedSlots))
                return Reject(owner, skill, "The backpack cannot hold the smelting result.",
                    ErrorMessageType.BagFull);

            var oldOutputCounts = bag.Items
                .Where(item => item.TemplateId == outcome.Output.ItemId &&
                               item.Grade == outputGrade)
                .ToDictionary(item => item.Id, item => item.Count);

            var paid = owner.TryPayCurrency(
                (uint)ContentCurrencyType.GoldWithAaPoint,
                definition.Gold,
                options.AutoUseAaPoint,
                ItemTaskType.GradeEnchant);
            if (!paid)
            {
                skill.Cancelled = true;
                return false;
            }

            if (!bag.TryConsumeExactItemsIntoTaskBatch(
                    [(target, definition.Amount), (catalyst, 1)], consumeTasks, forceRemove) ||
                !bag.TryConsumeExactTemplatesIntoTaskBatch(materials, consumeTasks, forceRemove))
            {
                Refund(owner, definition.Gold, options.AutoUseAaPoint);
                return Reject(owner, skill,
                    $"Smelting recipe {definition.Id} changed during its item transaction.",
                    ErrorMessageType.NotEnoughRequiredItem);
            }

            if (!bag.TryAcquireDefaultItemsIntoTaskBatch(rewards, rewardTasks))
                throw new InvalidOperationException(
                    "A preflighted AA10 item-smelting reward could not be acquired.");

            resultItem = bag.Items.FirstOrDefault(item =>
                item.TemplateId == outcome.Output.ItemId &&
                item.Grade == outputGrade &&
                item.Count > oldOutputCounts.GetValueOrDefault(item.Id));
            if (resultItem is null)
                throw new InvalidOperationException(
                    "AA10 item smelting acquired a reward but could not identify its item instance.");
        }

        foreach (var packet in ItemContainer.BuildIndependentItemTaskPackets(
                     ItemTaskType.GradeEnchant, consumeTasks, forceRemove))
            owner.SendPacket(packet);
        foreach (var rewardTask in rewardTasks)
            owner.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.GradeEnchant, rewardTask, []));

        owner.SendPacket(new SCItemSmeltingResultPacket(
            (sbyte)outcome.Result,
            false,
            (long)resultItem.Id,
            (int)resultItem.TemplateId));

        skill.LaborCostUnits = 1;
        Logger.Info(
            "AA10 item smelting: character={0}, recipe={1}, target={2}/{3}x{4}, catalyst={5}/{6}, " +
            "result={7}, output={8}/{9}@{10}, gold={11}, labor={12}, aaPoint={13}",
            owner.Name,
            definition.Id,
            target.Id,
            target.TemplateId,
            definition.Amount,
            catalyst.Id,
            catalyst.TemplateId,
            outcome.Result,
            resultItem.Id,
            resultItem.TemplateId,
            resultItem.Grade,
            definition.Gold,
            laborCost,
            options.AutoUseAaPoint);
        return true;
    }

    private static bool CanConsumeTemplates(
        IEnumerable<Item> items,
        IReadOnlyCollection<(uint TemplateId, int Amount)> requirements,
        out int freedSlots)
    {
        freedSlots = 0;
        foreach (var requirement in requirements
                     .GroupBy(entry => entry.TemplateId)
                     .Select(group => (TemplateId: group.Key, Amount: group.Sum(entry => entry.Amount))))
        {
            var remaining = requirement.Amount;
            foreach (var item in items
                         .Where(item => item.TemplateId == requirement.TemplateId && item.Count > 0)
                         .OrderBy(item => item.Slot))
            {
                var consumed = Math.Min(item.Count, remaining);
                if (consumed == item.Count)
                {
                    if (!item.CanDestroy())
                        return false;
                    freedSlots++;
                }
                remaining -= consumed;
                if (remaining == 0)
                    break;
            }
            if (remaining != 0)
                return false;
        }
        return true;
    }

    private static void Refund(Character owner, long gold, bool aaPoint)
    {
        if (gold <= 0)
            return;
        var refunded = aaPoint
            ? owner.AddAAPoint(SlotType.Inventory, gold)
            : owner.AddMoney(SlotType.Inventory, gold);
        if (!refunded)
            Logger.Error("Could not refund {0} smelting currency to {1}", gold, owner.Name);
    }

    private static bool Reject(
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
        Logger.Warn("Rejected AA10 item smelting for character {0}: {1}", owner?.Id ?? 0, reason);
        return false;
    }
}
