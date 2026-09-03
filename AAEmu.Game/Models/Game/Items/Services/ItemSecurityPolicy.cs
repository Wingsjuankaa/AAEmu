using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Models.Game.Items.Services;

public enum ItemSecurityOperation
{
    SameOwnerMove,
    Equip,
    Unequip,
    Repair,
    DurabilityLoss,
    DestroyOrConsume,
    TransferOwnership,
    IrreversibleTransform
}

public readonly record struct ItemSecurityTransition(
    ItemTaskType TaskType,
    byte PreviousFlags,
    bool IsUnsecureExcess,
    bool IsUnsecureSet);

/// <summary>One fail-closed policy for every server-side mutation of a secured item.</summary>
public static class ItemSecurityPolicy
{
    private static readonly HashSet<ItemTaskType> TransferTasks =
    [
        ItemTaskType.Auction,
        ItemTaskType.Mail,
        ItemTaskType.Trade,
        ItemTaskType.StoreSell,
        ItemTaskType.DeliverItemToOthers,
        ItemTaskType.Exchange
    ];

    public static bool CanPerform(Item item, ItemSecurityOperation operation)
    {
        if (item is null)
            return false;
        if (!item.HasFlag(ItemFlag.Secure))
            return true;

        return operation is
            ItemSecurityOperation.SameOwnerMove or
            ItemSecurityOperation.Equip or
            ItemSecurityOperation.Unequip or
            ItemSecurityOperation.Repair or
            ItemSecurityOperation.DurabilityLoss;
    }

    public static bool CanMove(Item item, ItemTaskType taskType, uint sourceOwnerId, uint targetOwnerId)
    {
        if (item is null)
            return false;
        if (!item.HasFlag(ItemFlag.Secure))
            return true;
        if (sourceOwnerId == 0 || targetOwnerId == 0 || sourceOwnerId != targetOwnerId ||
            TransferTasks.Contains(taskType))
            return false;
        return CanPerform(item, ItemSecurityOperation.SameOwnerMove);
    }

    public static bool TryLock(Item item, out ItemSecurityTransition transition)
    {
        transition = default;
        if (item is null)
            return false;

        lock (item)
        {
            var wasSecure = item.HasFlag(ItemFlag.Secure);
            var hadPendingUnlock = item.UnsecureTime != DateTime.MinValue;
            if (wasSecure && !hadPendingUnlock)
                return false;

            var previousFlags = (byte)item.ItemFlags;
            item.SetFlag(ItemFlag.Secure);
            item.UnsecureTime = DateTime.MinValue;
            transition = new ItemSecurityTransition(
                ItemTaskType.ItemLock, previousFlags, false, false);
            return true;
        }
    }

    public static bool TryUnlock(
        Item item,
        DateTime now,
        TimeSpan unlockDelay,
        out ItemSecurityTransition transition)
    {
        transition = default;
        if (item is null || unlockDelay <= TimeSpan.Zero)
            return false;

        lock (item)
        {
            if (!item.HasFlag(ItemFlag.Secure))
                return false;

            var previousFlags = (byte)item.ItemFlags;
            if (item.UnsecureTime == DateTime.MinValue)
            {
                item.UnsecureTime = now.Add(unlockDelay);
                transition = new ItemSecurityTransition(
                    ItemTaskType.ItemUnlock, previousFlags, false, true);
                return true;
            }

            if (item.UnsecureTime > now)
                return false;

            item.RemoveFlag(ItemFlag.Secure);
            item.UnsecureTime = DateTime.MinValue;
            transition = new ItemSecurityTransition(
                ItemTaskType.ItemUnlockExcess, previousFlags, true, false);
            return true;
        }
    }
}
