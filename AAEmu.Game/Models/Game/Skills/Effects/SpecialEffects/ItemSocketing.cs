using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Installs r575 Lunagem items through the Gear Upgrade socket context (SkillObject type 10).
/// </summary>
public class ItemSocketing : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemSocketing;

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
            targetObj is not SkillCastItemTarget itemTarget ||
            skillObject is not SkillObjectSocketInstallOptions options)
        {
            Reject(owner: caster as Character, skill, null, null,
                "The request did not contain the native r575 socket-install context.");
            return;
        }

        var targetItem = owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
        var reagent = owner.Inventory.GetItemById(reagentCaster.ItemId);
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
            Reject(owner, skill, targetItem, reagent, validation.Reason, false);
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
        bool sendMappedError = true)
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
            1,
            false));
        Logger.Warn("Rejected AA10 Lunagem operation for character {0}: {1}", owner.Id, reason);
    }
}
