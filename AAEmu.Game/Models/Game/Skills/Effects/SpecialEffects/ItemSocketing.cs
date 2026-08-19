using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Executes r575 Lunagem installation, destructive removal and extraction through the Gear Upgrade
/// socket contexts (SkillObject type 10 for install/remove and type 11 for extraction).
/// </summary>
public class ItemSocketing : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemSocketing;

    internal static bool IsExtractionFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.socketExtract);

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
        // Socketing owns the exact reagent transaction. The generic skill cleanup must never consume
        // a second Lunagem after this effect succeeds, nor consume one when validation rejects it.
        skill.SkipAutomaticItemConsumption = true;

        if (caster is not Character owner ||
            casterObj is not SkillItem reagentCaster ||
            targetObj is not SkillCastItemTarget itemTarget)
        {
            Reject(owner: caster as Character, skill, null, null,
                "The request did not contain the native r575 socket context.",
                operation: NormalizeOperation(value1));
            return;
        }

        var targetItem = owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
        var reagent = owner.Inventory.GetItemById(reagentCaster.ItemId);
        if (targetItem is null || reagent is null || reagent.Template.UseSkillId != skill.Template.Id)
        {
            Reject(owner, skill, targetItem, reagent,
                "The target, source item or source item's use skill does not match this request.",
                operation: NormalizeOperation(value1));
            return;
        }

        SkillObjectSocketInstallOptions options = null;
        switch (value1)
        {
            case 0:
                if (skillObject is not SkillObjectSocketInstallOptions)
                {
                    Reject(owner, skill, targetItem, reagent,
                        "Removal did not contain the native r575 type-10 socket context.", operation: 0);
                    return;
                }
                ExecuteRemoval(owner, targetItem, reagent, skill);
                return;
            case 1:
                if (skillObject is not SkillObjectSocketInstallOptions installOptions)
                {
                    Reject(owner, skill, targetItem, reagent,
                        "Installation did not contain the native r575 type-10 socket context.");
                    return;
                }
                options = installOptions;
                break;
            case 2:
                if (skillObject is not SkillObjectSocketExtractOptions extractionOptions)
                {
                    Reject(owner, skill, targetItem, reagent,
                        "Extraction did not contain the native r575 type-11 socket context.", operation: 2);
                    return;
                }
                ExecuteExtraction(owner, targetItem, reagent, skill, extractionOptions);
                return;
            default:
                Reject(owner, skill, targetItem, reagent,
                    $"Unsupported native socket operation {value1}.",
                    operation: NormalizeOperation(value1));
                return;
        }

        var validation = ItemSocketRuleService.Instance.Validate(targetItem, reagent);
        if (!validation.IsValid)
        {
            Logger.Warn(
                "Blocked AA10 socket request owner={0}, target={1}, reagent={2}: {3} ({4})",
                owner.Id,
                targetItem?.Id ?? 0,
                reagent?.TemplateId ?? 0,
                validation.Failure,
                validation.Reason);
            SendValidationFailure(owner, validation);
            Reject(owner, skill, targetItem, reagent, validation.Reason, false, 1);
            return;
        }

        var requestedCount = options.Count == 0 ? 1u : options.Count;
        if (requestedCount > int.MaxValue)
        {
            Reject(owner, skill, targetItem, reagent, "The requested socket count is too large.");
            return;
        }

        var count = (int)requestedCount;
        var availableSockets = validation.MaximumSockets - validation.OccupiedSockets;
        var availableReagents = owner.Inventory.GetItemsCount(reagent.TemplateId);
        if (count < 1 || count > availableSockets || count > availableReagents)
        {
            if (count > availableSockets)
                owner.SendErrorMessage(ErrorMessageType.ItemSocketsFull);
            else
                owner.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            Reject(owner, skill, targetItem, reagent,
                $"Requested {count} sockets, but only {availableSockets} slots and " +
                $"{availableReagents} reagents are available.", false);
            return;
        }

        // A multi-install request is atomic. It is safe only when every requested socket is guaranteed;
        // probabilistic profiles are processed one at a time so a failure cannot ambiguously consume a
        // partial amount or break a subset of the existing gems.
        if (count > 1 && !validation.ChanceDefinition.IsGuaranteed(validation.OccupiedSockets, count))
        {
            Reject(owner, skill, targetItem, reagent,
                "Multiple Lunagem installation is allowed only when every requested socket is guaranteed.");
            return;
        }

        long totalCost = 0;
        for (var offset = 0; offset < count; offset++)
        {
            var operationValidation = new ItemSocketValidationResult
            {
                Definition = validation.Definition,
                ChanceDefinition = validation.ChanceDefinition,
                OccupiedSockets = validation.OccupiedSockets + offset,
                MaximumSockets = validation.MaximumSockets,
                SuccessChance = validation.ChanceDefinition.GetInstallChance(
                    validation.OccupiedSockets + offset)
            };
            if (operationValidation.SuccessChance is null or <= 0 ||
                !ItemSocketRuleService.Instance.TryCalculateCost(
                    owner, targetItem, reagent, operationValidation, operationValidation.OccupiedSockets,
                    out var operationCost))
            {
                Reject(owner, skill, targetItem, reagent,
                    "The native r575 socket probability or cost could not be resolved.");
                return;
            }

            totalCost += operationCost;
            if (totalCost > int.MaxValue)
            {
                Reject(owner, skill, targetItem, reagent,
                    "The socketing cost exceeds the supported currency range.");
                return;
            }
        }

        var socketIndexes = new List<int>(count);
        for (var index = 0; index < validation.MaximumSockets && socketIndexes.Count < count; index++)
        {
            if (targetItem.GemData[EquipItem.NativeSocketStartIndex + index] == 0)
                socketIndexes.Add(index);
        }
        if (socketIndexes.Count != count)
        {
            owner.SendErrorMessage(ErrorMessageType.ItemSocketsFull);
            Reject(owner, skill, targetItem, reagent,
                "The target socket layout changed while the request was being validated.", false);
            return;
        }

        var originalGemData = (uint[])targetItem.GemData.Clone();
        var originalDirty = targetItem.IsDirty;
        var success = true;
        for (var operationIndex = 0; operationIndex < socketIndexes.Count; operationIndex++)
        {
            var socketIndex = socketIndexes[operationIndex];
            var chance = validation.ChanceDefinition.GetInstallChance(
                validation.OccupiedSockets + operationIndex);
            if (chance is null || Random.Shared.Next(0, 10000) >= chance.Value)
            {
                success = false;
                if (validation.ChanceDefinition.FailBreak)
                {
                    for (var index = 0; index < EquipItem.NativeSocketCapacity; index++)
                        targetItem.SetNativeSocket(index, 0);
                }
                break;
            }

            if (!targetItem.SetNativeSocket(socketIndex, reagent.TemplateId))
            {
                targetItem.GemData = originalGemData;
                targetItem.IsDirty = originalDirty;
                Reject(owner, skill, targetItem, reagent,
                    "The target socket could not be updated.");
                return;
            }
        }

        // The r575 Gear Upgrade controller snapshots the target after the first Socketing transaction.
        // Preflight the wallet here, then publish wallet + reagent + target together below. Sending these
        // as independent packets leaves the visible socket list one operation behind until Equip is clicked.
        var useAaPoint = options.AutoUseAaPoint;
        if ((useAaPoint ? owner.AaPoint : owner.Money) < totalCost)
        {
            targetItem.GemData = originalGemData;
            targetItem.IsDirty = originalDirty;
            owner.SendErrorMessage(useAaPoint
                ? ErrorMessageType.NotEnoughAaPoint
                : ErrorMessageType.NotEnoughMoney);
            Reject(owner, skill, targetItem, reagent, "The selected currency is insufficient.", false);
            return;
        }

        // r575 must see UpdateDetail before any variable-sized Take action in this batch. The inverse
        // ordering was tested manually and made both the selected frame and the bag item stale.
        var socketTasks = new List<ItemTask> { new ItemUpdate(targetItem) };
        var forceRemove = new List<ulong>();
        if (totalCost > 0)
        {
            if (useAaPoint)
            {
                owner.AaPoint -= totalCost;
                socketTasks.Add(new AAPointUpdate(-totalCost));
            }
            else
            {
                owner.Money -= totalCost;
                socketTasks.Add(new MoneyChange(-totalCost));
            }
        }

        if (!owner.Inventory.Bag.TryConsumeExactTemplatesIntoTaskBatch(
                [(reagent.TemplateId, count)],
                socketTasks,
                forceRemove))
        {
            targetItem.GemData = originalGemData;
            targetItem.IsDirty = originalDirty;
            if (useAaPoint)
                owner.AaPoint += totalCost;
            else
                owner.Money += totalCost;
            Reject(owner, skill, targetItem, reagent,
                "The Lunagem reagent transaction could not be committed.");
            return;
        }

        targetItem.IsDirty = true;
        if (targetItem.SlotType == SlotType.Equipment)
            owner.UpdateGearBonuses(null, null);

        // AA10 r575's ItemSocketInsert controller listens to the per-action item event (0x21), but
        // only accepts ItemTaskType 0x2A. It records the matching selected-item template there and
        // uses the subsequent 0xCA / native event 0x5A as the second half of the refresh gate.
        // Socketing (99) applies the bag mutations but never opens that gate, leaving the frame stale.
        owner.SendPacket(new SCItemTaskSuccessPacket(
            ItemTaskType.SkillEffectGainItem,
            socketTasks,
            forceRemove));

        // r575 keeps two item views for this screen. UpdateDetail drives the normal item-task change
        // set, while SCItemDetailUpdated publishes the compact detail to the live bag item. They are
        // deliberately separate: omitting the latter leaves the inventory tooltip one operation
        // behind even though the server state and the enchant controller transaction succeeded.
        owner.SendPacket(new SCItemDetailUpdatedPacket(targetItem));

        owner.SendPacket(new SCItemSocketingResultPacket(
            success ? (byte)1 : (byte)0,
            targetItem.Id,
            reagent.TemplateId,
            1,
            true));

        Logger.Info(
            "AA10 Lunagem operation: character={0}, target={1}/{2}, reagent={3}, sockets={4}, " +
            "success={5}, failBreak={6}, cost={7}, currency={8}",
            owner.Name,
            targetItem.Id,
            targetItem.TemplateId,
            reagent.TemplateId,
            string.Join(",", socketIndexes),
            success,
            validation.ChanceDefinition.FailBreak,
            totalCost,
            options.AutoUseAaPoint ? "aaPoint" : "money");
    }

    private static void ExecuteRemoval(
        Character owner,
        EquipItem targetItem,
        Item reagent,
        Skill skill)
    {
        var socketIndexes = Enumerable.Range(0, EquipItem.NativeSocketCapacity)
            .Where(index => targetItem.GemData[EquipItem.NativeSocketStartIndex + index] != 0)
            .ToArray();
        if (socketIndexes.Length == 0)
        {
            owner.SendErrorMessage(ErrorMessageType.ItemSocketsEmpty);
            Reject(owner, skill, targetItem, reagent,
                "The target has no Lunagems to remove.", false, 0);
            return;
        }

        if (owner.Inventory.GetItemsCount(reagent.TemplateId) < 1)
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            Reject(owner, skill, targetItem, reagent,
                "The destructive removal item is missing.", false, 0);
            return;
        }

        var originalGemData = (uint[])targetItem.GemData.Clone();
        var originalDirty = targetItem.IsDirty;
        foreach (var index in socketIndexes)
            targetItem.SetNativeSocket(index, 0);

        var tasks = new List<ItemTask> { new ItemUpdate(targetItem) };
        var forceRemove = new List<ulong>();
        if (!owner.Inventory.Bag.TryConsumeExactTemplatesIntoTaskBatch(
                [(reagent.TemplateId, 1)], tasks, forceRemove))
        {
            targetItem.GemData = originalGemData;
            targetItem.IsDirty = originalDirty;
            Reject(owner, skill, targetItem, reagent,
                "The destructive removal item transaction could not be committed.",
                operation: 0);
            return;
        }

        PublishSocketMutation(owner, targetItem, reagent.TemplateId, 0, tasks, forceRemove, []);
        Logger.Info(
            "AA10 Lunagem removal: character={0}, target={1}/{2}, reagent={3}, removed={4}",
            owner.Name,
            targetItem.Id,
            targetItem.TemplateId,
            reagent.TemplateId,
            string.Join(",", socketIndexes));
    }

    private static void ExecuteExtraction(
        Character owner,
        EquipItem targetItem,
        Item reagent,
        Skill skill,
        SkillObjectSocketExtractOptions options)
    {
        // The same r575 feature bit exposes the Extract subtab in socket_enchant.lua. Refuse the
        // server transaction when it is absent so a forged request cannot bypass the client gate.
        if (!IsExtractionFeatureEnabled(FeaturesManager.Fsets))
        {
            Reject(owner, skill, targetItem, reagent,
                "Lunagem extraction is disabled by the socketExtract feature flag.",
                operation: 2);
            return;
        }

        var plan = ItemSocketRuleService.Instance.PlanExtraction(
            targetItem,
            options.SocketIndex,
            options.ExtractAll);
        if (!plan.IsValid)
        {
            SendExtractionFailure(owner, plan.Failure);
            Reject(owner, skill, targetItem, reagent, plan.Reason, false, 2);
            return;
        }

        var processedCount = plan.SocketIndexes.Count;
        if (owner.Inventory.GetItemsCount(reagent.TemplateId) < processedCount)
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            Reject(owner, skill, targetItem, reagent,
                $"Extraction needs {processedCount} source items.", false, 2);
            return;
        }

        var laborCost = skill.CalculateLaborCost(owner, processedCount);
        if (laborCost <= 0 || laborCost > short.MaxValue ||
            owner.LaborPower + owner.LocalLaborPower < laborCost)
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughLaborPower);
            Reject(owner, skill, targetItem, reagent,
                $"Extraction needs {laborCost} labor for {processedCount} sockets.", false, 2);
            return;
        }

        var rewards = plan.ReturnedItems
            .Select(entry => (entry.Key, entry.Value))
            .ToArray();
        var bag = owner.Inventory.Bag;
        var tasks = new List<ItemTask> { new ItemUpdate(targetItem) };
        var rewardTasks = new List<ItemTask>();
        var forceRemove = new List<ulong>();
        var originalGemData = (uint[])targetItem.GemData.Clone();
        var originalDirty = targetItem.IsDirty;

        lock (bag.Items)
        {
            // The source stack can release a slot that the returned Lunagem immediately occupies.
            var freedSlots = CountFullyConsumedStacks(bag.Items, reagent.TemplateId, processedCount);
            if (!bag.CanAcquireDefaultTemplates(rewards, freedSlots))
            {
                owner.SendErrorMessage(ErrorMessageType.BagFull);
                Reject(owner, skill, targetItem, reagent,
                    "The bag cannot hold every extracted Lunagem.", false, 2);
                return;
            }

            foreach (var index in plan.SocketIndexes)
                targetItem.SetNativeSocket(index, 0);

            if (!bag.TryConsumeExactTemplatesIntoTaskBatch(
                    [(reagent.TemplateId, processedCount)], tasks, forceRemove))
            {
                targetItem.GemData = originalGemData;
                targetItem.IsDirty = originalDirty;
                Reject(owner, skill, targetItem, reagent,
                    "The extraction item transaction could not be committed.",
                    operation: 2);
                return;
            }

            // Capacity and templates were preflighted under the same re-entrant bag lock. A failure
            // here indicates an internal invariant violation rather than a player validation error.
            if (!bag.TryAcquireDefaultTemplatesIntoTaskBatch(rewards, rewardTasks))
                throw new InvalidOperationException(
                    "A preflighted Lunagem extraction reward could not be acquired.");
        }

        skill.LaborCostUnits = processedCount;
        PublishSocketMutation(
            owner,
            targetItem,
            reagent.TemplateId,
            2,
            tasks,
            forceRemove,
            rewardTasks);
        Logger.Info(
            "AA10 Lunagem extraction: character={0}, target={1}/{2}, reagent={3}, sockets={4}, " +
            "returned={5}, destroyed={6}, labor={7}, all={8}",
            owner.Name,
            targetItem.Id,
            targetItem.TemplateId,
            reagent.TemplateId,
            string.Join(",", plan.SocketIndexes),
            string.Join(",", plan.ReturnedItems.Select(entry => $"{entry.Key}x{entry.Value}")),
            string.Join(",", plan.DestroyedItemIds),
            laborCost,
            options.ExtractAll);
    }

    private static int CountFullyConsumedStacks(
        IEnumerable<Item> items,
        uint templateId,
        int amount)
    {
        var remaining = amount;
        var freedSlots = 0;
        foreach (var item in items
                     .Where(entry => entry.TemplateId == templateId && entry.Count > 0)
                     .OrderBy(entry => entry.Slot))
        {
            var consumed = Math.Min(item.Count, remaining);
            if (consumed == item.Count)
                freedSlots++;
            remaining -= consumed;
            if (remaining == 0)
                break;
        }

        return freedSlots;
    }

    private static void PublishSocketMutation(
        Character owner,
        EquipItem targetItem,
        uint reagentTemplateId,
        byte operation,
        List<ItemTask> tasks,
        List<ulong> forceRemove,
        IEnumerable<ItemTask> rewardTasks)
    {
        targetItem.IsDirty = true;
        if (targetItem.SlotType == SlotType.Equipment)
            owner.UpdateGearBonuses(null, null);

        owner.SendPacket(new SCItemTaskSuccessPacket(
            ItemTaskType.SkillEffectGainItem,
            tasks,
            forceRemove));

        // Keep every returned Take body on its own packet boundary. AA10 otherwise applies only the
        // first variable-sized reward in multi-item transactions until the next relog.
        foreach (var rewardTask in rewardTasks)
            owner.SendPacket(new SCItemTaskSuccessPacket(
                ItemTaskType.SkillEffectGainItem,
                rewardTask,
                []));

        owner.SendPacket(new SCItemDetailUpdatedPacket(targetItem));
        owner.SendPacket(new SCItemSocketingResultPacket(
            1,
            targetItem.Id,
            reagentTemplateId,
            operation,
            true));
    }

    private static void SendExtractionFailure(
        Character owner,
        ItemSocketExtractionFailure failure)
    {
        owner.SendErrorMessage(failure switch
        {
            ItemSocketExtractionFailure.SocketsEmpty => ErrorMessageType.ItemSocketsEmpty,
            ItemSocketExtractionFailure.InvalidTarget or
                ItemSocketExtractionFailure.InvalidSocketIndex => ErrorMessageType.InvalidTarget,
            _ => ErrorMessageType.Invalid
        });
    }

    private static byte NormalizeOperation(int value) =>
        value is >= byte.MinValue and <= byte.MaxValue ? (byte)value : byte.MaxValue;

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
            case ItemSocketValidationFailure.DefinitionMissing:
            case ItemSocketValidationFailure.ExplicitItemMismatch:
            case ItemSocketValidationFailure.SlotMismatch:
                owner.SendErrorMessage(ErrorMessageType.InvalidTarget);
                break;
            default:
                owner.SendErrorMessage(ErrorMessageType.Invalid);
                break;
        }
    }

    private static void Reject(
        Character owner,
        Skill skill,
        EquipItem targetItem,
        Item reagent,
        string reason,
        bool sendMappedError = true,
        byte operation = 1)
    {
        if (skill is not null)
        {
            skill.SkipAutomaticItemConsumption = true;
            skill.Cancelled = true;
        }

        if (owner is null)
            return;

        if (sendMappedError)
            owner.SendErrorMessage(ErrorMessageType.Invalid);
        owner.SendPacket(new SCItemSocketingResultPacket(
            0,
            targetItem?.Id ?? 0,
            reagent?.TemplateId ?? 0,
            operation,
            false));
        Logger.Warn("Rejected AA10 Lunagem operation for character {0}: {1}", owner.Id, reason);
    }
}
