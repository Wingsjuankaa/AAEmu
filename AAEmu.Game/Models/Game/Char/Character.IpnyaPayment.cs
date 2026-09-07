using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Models.Game.Char;

public partial class Character
{
    internal bool CanPayEquipSlotReinforce(EquipSlotReinforcePlan plan) =>
        Inventory?.Bag != null && TryCommitEquipSlotReinforce(plan, [], [], null, validateOnly: true);

    /// <summary>The persistence gate is owned by the caller. No mutation before durableCommit succeeds.</summary>
    internal bool TryCommitEquipSlotReinforce(EquipSlotReinforcePlan plan, List<ItemTask> tasks,
        List<ulong> removals, Action<IReadOnlyCollection<(Item Item, int Amount)>, long, long> durableCommit,
        bool validateOnly = false)
    {
        lock (_walletLock)
        lock (Inventory.Bag.Items)
        {
            if (plan.Cost < 0 || (plan.UseAaPoint ? AaPoint : Money) < plan.Cost || plan.Materials.Count == 0)
                return false;
            var selected = new List<(Item Item, int Amount)>();
            foreach (var group in plan.Materials.GroupBy(r => r.Item))
            {
                if (group.Key == 0 || group.Any(r => r.Count <= 0)) return false;
                var remaining = group.Sum(r => r.Count);
                foreach (var item in Inventory.Bag.Items.Where(i => i.TemplateId == group.Key && i.Count > 0)
                             .OrderBy(i => i.Slot))
                {
                    if (!item.CanDestroy() || !ReferenceEquals(item._holdingContainer, Inventory.Bag)) continue;
                    var count = Math.Min(remaining, item.Count);
                    selected.Add((item, count)); remaining -= count;
                    if (remaining == 0) break;
                }
                if (remaining != 0) return false;
            }
            if (selected.Select(x => x.Item.Id).Distinct().Count() != selected.Count) return false;
            if (validateOnly) return true;
            var gold = Money - (plan.UseAaPoint ? 0 : plan.Cost);
            var aa = AaPoint - (plan.UseAaPoint ? plan.Cost : 0);
            durableCommit(selected, gold, aa);
            Money = gold; AaPoint = aa;
            if (!Inventory.Bag.TryConsumeExactItemsIntoTaskBatch(selected, tasks, removals, isolateNotifications: true))
                throw new InvalidOperationException("A locked, preflighted Ipnya consumption changed after commit.");
            if (plan.Cost > 0)
                tasks.Add(plan.UseAaPoint ? new AAPointUpdate(-plan.Cost) : new MoneyChange(-plan.Cost));
            return true;
        }
    }
}
