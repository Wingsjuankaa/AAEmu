using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Services;
using NLog;

namespace AAEmu.Game.Core.Managers;

public sealed class ItemSecurityService(TimeProvider timeProvider) : Singleton<ItemSecurityService>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    public bool LockItem(ICharacter character, SlotType slotType, byte slot, ulong itemId)
    {
        if (!IsFeatureEnabled() || !TryGetOwnedContainer(character, slotType, out var container))
            return Reject(character, ErrorMessageType.ItemSecureCondition);

        Item item;
        ItemSecurityTransition transition;
        lock (container.Items)
        {
            if (!TryResolveOwnedItem(character, container, slotType, slot, itemId, out item) ||
                !ItemSecurityGameData.Instance.IsEligible(item.Template) ||
                !ItemSecurityPolicy.TryLock(item, out transition))
                return Reject(character, ErrorMessageType.ItemSecureCondition);
        }

        Publish(character, item, transition);
        return true;
    }

    public bool UnlockItem(ICharacter character, SlotType slotType, byte slot, ulong itemId)
    {
        if (!IsFeatureEnabled() || !TryGetOwnedContainer(character, slotType, out var container))
            return Reject(character, ErrorMessageType.ItemSecureCondition);

        Item item;
        ItemSecurityTransition transition;
        lock (container.Items)
        {
            if (!TryResolveOwnedItem(character, container, slotType, slot, itemId, out item) ||
                !ItemSecurityGameData.Instance.IsEligible(item.Template) ||
                !ItemSecurityPolicy.TryUnlock(
                    item,
                    timeProvider.GetUtcNow().UtcDateTime,
                    ItemSecurityGameData.Instance.UnlockDelay,
                    out transition))
                return Reject(character, ErrorMessageType.ItemSecureCondition);
        }

        Publish(character, item, transition);
        return true;
    }

    public int LockEquipment(ICharacter character)
    {
        if (!IsFeatureEnabled() || character?.Inventory?.Equipment is null)
        {
            Reject(character, ErrorMessageType.AllEquipmentsAreSecured);
            return 0;
        }

        var equipment = character.Inventory.Equipment;
        var tasks = new List<ItemTask>();
        lock (equipment.Items)
        {
            foreach (var item in equipment.Items.ToArray())
            {
                if (!IsOwnedBy(character, item) || !ItemSecurityGameData.Instance.IsEligible(item.Template) ||
                    !ItemSecurityPolicy.TryLock(item, out var transition))
                    continue;
                tasks.Add(CreateUpdate(item, transition));
            }
        }

        if (tasks.Count == 0)
        {
            Reject(character, ErrorMessageType.AllEquipmentsAreSecured);
            return 0;
        }

        character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.ItemLock, tasks, []));
        return tasks.Count;
    }

    public int UnlockEquipment(ICharacter character)
    {
        if (!IsFeatureEnabled() || character?.Inventory?.Equipment is null)
        {
            Reject(character, ErrorMessageType.AllEquipmentsAreUnsecured);
            return 0;
        }

        var equipment = character.Inventory.Equipment;
        var now = timeProvider.GetUtcNow().UtcDateTime;
        var grouped = new Dictionary<ItemTaskType, List<ItemTask>>();
        lock (equipment.Items)
        {
            foreach (var item in equipment.Items.ToArray())
            {
                if (!IsOwnedBy(character, item) || !ItemSecurityGameData.Instance.IsEligible(item.Template) ||
                    !ItemSecurityPolicy.TryUnlock(
                        item, now, ItemSecurityGameData.Instance.UnlockDelay, out var transition))
                    continue;

                if (!grouped.TryGetValue(transition.TaskType, out var tasks))
                    grouped[transition.TaskType] = tasks = [];
                tasks.Add(CreateUpdate(item, transition));
            }
        }

        if (grouped.Count == 0)
        {
            Reject(character, ErrorMessageType.AllEquipmentsAreUnsecured);
            return 0;
        }

        foreach (var (taskType, tasks) in grouped)
            character.SendPacket(new SCItemTaskSuccessPacket(taskType, tasks, []));
        return grouped.Values.Sum(tasks => tasks.Count);
    }

    private static bool IsFeatureEnabled() =>
        FeaturesManager.Fsets?.Check(Feature.itemSecure) == true;

    private static bool TryGetOwnedContainer(ICharacter character, SlotType slotType, out ItemContainer container)
    {
        container = null;
        return character?.Inventory is not null &&
               slotType is SlotType.Equipment or SlotType.Inventory or SlotType.Bank &&
               character.Inventory._itemContainers.TryGetValue(slotType, out container) &&
               container.OwnerId == character.Id;
    }

    private static bool TryResolveOwnedItem(
        ICharacter character,
        ItemContainer container,
        SlotType slotType,
        byte slot,
        ulong itemId,
        out Item item)
    {
        item = null;
        if (character?.Inventory is null || container is null)
            return false;

        item = container.GetItemBySlot(slot);
        return item is not null && item.Id == itemId && IsOwnedBy(character, item) &&
               item.SlotType == slotType && item.Slot == slot;
    }

    private static bool IsOwnedBy(ICharacter character, Item item) =>
        character is not null && item is not null && item.OwnerId == character.Id &&
        item._holdingContainer is not null &&
        item._holdingContainer.OwnerId == character.Id &&
        item._holdingContainer.Items.Contains(item);

    private static ItemUpdateSecurity CreateUpdate(Item item, ItemSecurityTransition transition) =>
        new(
            item,
            (byte)item.ItemFlags,
            transition.IsUnsecureExcess,
            transition.IsUnsecureSet,
            item.HasFlag(ItemFlag.Unpacked),
            transition.PreviousFlags);

    private static void Publish(ICharacter character, Item item, ItemSecurityTransition transition)
    {
        character.SendPacket(new SCItemTaskSuccessPacket(
            transition.TaskType,
            CreateUpdate(item, transition),
            []));
        Logger.Info(
            "AA10 Item Lock: character={0}, item={1}/{2}, task={3}, flags=0x{4:X2}, unlock={5:o}",
            character.Id,
            item.Id,
            item.TemplateId,
            transition.TaskType,
            (byte)item.ItemFlags,
            item.UnsecureTime);
    }

    private static bool Reject(ICharacter character, ErrorMessageType error)
    {
        character?.SendErrorMessage(error);
        return false;
    }
}
