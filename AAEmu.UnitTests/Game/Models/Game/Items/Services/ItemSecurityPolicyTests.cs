using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Services;

public class ItemSecurityPolicyTests
{
    private static readonly DateTime Now = new(2026, 8, 31, 12, 0, 0, DateTimeKind.Utc);
    private static readonly TimeSpan Delay = TimeSpan.FromHours(72);

    [Test]
    public async Task Lock_UnlockAndExpiry_FollowTheR575StateMachine()
    {
        var item = CreateItem();

        var locked = ItemSecurityPolicy.TryLock(item, out var lockTransition);
        await Assert.That(locked).IsTrue();
        await Assert.That(item.IsDirty).IsTrue();
        await Assert.That(item.HasFlag(ItemFlag.Secure)).IsTrue();
        await Assert.That(item.UnsecureTime).IsEqualTo(DateTime.MinValue);
        await Assert.That(lockTransition.TaskType).IsEqualTo(ItemTaskType.ItemLock);

        var scheduled = ItemSecurityPolicy.TryUnlock(item, Now, Delay, out var unlockTransition);
        await Assert.That(scheduled).IsTrue();
        await Assert.That(item.HasFlag(ItemFlag.Secure)).IsTrue();
        await Assert.That(item.UnsecureTime).IsEqualTo(Now.Add(Delay));
        await Assert.That(unlockTransition.TaskType).IsEqualTo(ItemTaskType.ItemUnlock);
        await Assert.That(unlockTransition.IsUnsecureSet).IsTrue();

        var originalDeadline = item.UnsecureTime;
        item.IsDirty = false;
        var repeated = ItemSecurityPolicy.TryUnlock(item, Now.AddHours(1), Delay, out _);
        await Assert.That(repeated).IsFalse();
        await Assert.That(item.IsDirty).IsFalse();
        await Assert.That(item.UnsecureTime).IsEqualTo(originalDeadline);

        var completed = ItemSecurityPolicy.TryUnlock(item, originalDeadline, Delay, out var excessTransition);
        await Assert.That(completed).IsTrue();
        await Assert.That(item.HasFlag(ItemFlag.Secure)).IsFalse();
        await Assert.That(item.UnsecureTime).IsEqualTo(DateTime.MinValue);
        await Assert.That(excessTransition.TaskType).IsEqualTo(ItemTaskType.ItemUnlockExcess);
        await Assert.That(excessTransition.IsUnsecureExcess).IsTrue();
    }

    [Test]
    public async Task LockDuringPendingUnlock_CancelsDeadlineWithoutDroppingProtection()
    {
        var item = CreateItem();
        ItemSecurityPolicy.TryLock(item, out _);
        ItemSecurityPolicy.TryUnlock(item, Now, Delay, out _);

        var changed = ItemSecurityPolicy.TryLock(item, out var transition);

        await Assert.That(changed).IsTrue();
        await Assert.That(item.HasFlag(ItemFlag.Secure)).IsTrue();
        await Assert.That(item.UnsecureTime).IsEqualTo(DateTime.MinValue);
        await Assert.That(transition.TaskType).IsEqualTo(ItemTaskType.ItemLock);
    }

    [Test]
    public async Task ConcurrentLock_CommitsExactlyOneTransition()
    {
        var item = CreateItem();
        var successes = 0;

        Parallel.For(0, 16, iteration =>
        {
            if (ItemSecurityPolicy.TryLock(item, out _))
                Interlocked.Increment(ref successes);
        });

        await Assert.That(successes).IsEqualTo(1);
        await Assert.That(item.HasFlag(ItemFlag.Secure)).IsTrue();
    }

    [Test]
    public async Task SecuredItem_AllowsSafeOwnerActionsAndBlocksLossOrTransfer()
    {
        var item = CreateItem();
        item.SetFlag(ItemFlag.Secure);

        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.SameOwnerMove)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.Equip)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.Unequip)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.Repair)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.DurabilityLoss)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.DestroyOrConsume)).IsFalse();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.TransferOwnership)).IsFalse();
        await Assert.That(ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.IrreversibleTransform)).IsFalse();
        await Assert.That(ItemSecurityPolicy.CanMove(item, ItemTaskType.SwapItems, 7, 7)).IsTrue();
        await Assert.That(ItemSecurityPolicy.CanMove(item, ItemTaskType.Mail, 7, 7)).IsFalse();
        await Assert.That(ItemSecurityPolicy.CanMove(item, ItemTaskType.Invalid, 7, 8)).IsFalse();
    }

    private static Item CreateItem() =>
        new(100, new ItemTemplate { Id = 200, CategoryId = 10, MaxCount = 1 }, 1);
}
