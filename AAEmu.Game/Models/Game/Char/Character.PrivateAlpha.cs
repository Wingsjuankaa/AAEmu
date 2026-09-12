using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.PrivateAlpha;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Char;

public partial class Character
{
    internal bool GrantAlphaPoints(GamePointKind kind, int amount)
    {
        lock (GamePersistence.Sync)
        {
            if (kind is not (GamePointKind.Honor or GamePointKind.Vocation)) return false;
            var current = kind == GamePointKind.Honor ? HonorPoint : VocationPoint;
            if (!AlphaRules.TryPoints(current, amount, out var next)) return false;
            var column = kind == GamePointKind.Honor ? "honor_point" : "vocation_point";
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText = $"UPDATE characters SET {column}=@next WHERE id=@id";
            command.Parameters.AddWithValue("@next", next); command.Parameters.AddWithValue("@id", Id);
            if (command.ExecuteNonQuery() != 1) return false;
            if (kind == GamePointKind.Honor) HonorPoint = next;
            else VocationPoint = next;
        }
        // Exact test grants do not apply gain buffs or advance gameplay quests.
        SendPacket(new SCCharacterGamePointsPacket(this));
        SendPacket(new SCGamePointChangedPacket((byte)kind, amount));
        return true;
    }

    internal bool GrantAlphaGold(int gold)
    {
        long delta;
        lock (GamePersistence.Sync)
        lock (_walletLock)
        {
            if (!AlphaRules.TryGold(Money, gold, AppConfiguration.Instance.PrivateAlpha.MaxGoldPerRequest, out var next)) return false;
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText = "UPDATE characters SET money=@next WHERE id=@id";
            command.Parameters.AddWithValue("@next", next); command.Parameters.AddWithValue("@id", Id);
            if (command.ExecuteNonQuery() != 1) return false;
            delta = next - Money; Money = next;
        }
        SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.Gm, [new MoneyChange(delta)], []));
        return true;
    }

    internal bool GrantAlphaLabor(int amount)
    {
        int delta;
        lock (GamePersistence.Sync)
        lock (_laborLock)
        {
            var cap = Math.Clamp(AppConfiguration.Instance.PrivateAlpha.LaborCap, 1, short.MaxValue);
            if (!AlphaRules.ValidAmount(amount, cap)) return false;
            var next = Math.Min(cap, LaborPower + amount);
            delta = next - LaborPower;
            if (delta <= 0) return false;
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText = "UPDATE accounts SET labor=@next WHERE account_id=@id";
            command.Parameters.AddWithValue("@next", next); command.Parameters.AddWithValue("@id", AccountId);
            if (command.ExecuteNonQuery() != 1) return false;
            // The durable write succeeded; do not invoke the property setter's second DB write.
            _laborPower = (short)next;
        }
        SendPacket(new SCCharacterLaborPowerChangedPacket(delta, 0, 0, 0, 0, 0));
        return true;
    }

    /// <summary>Plan unmerged stacks, persist them, then publish the existing inventory lifecycle.
    /// Failed persistence never adds items, fires acquisition events or sends inventory packets.</summary>
    internal bool GrantAlphaItems(uint templateId, int count, byte grade, uint? grantAccessBy = null)
    {
        var bag = Inventory.Bag;
        var manager = ItemManager.Instance;
        List<Item> planned = [];
        lock (GamePersistence.Sync)
        lock (bag.Items)
        {
            var template = manager.GetTemplate(templateId);
            if (template is null || count <= 0 || template.MaxCount <= 0 || grade > 12) return false;
            var needed = AlphaRules.StacksNeeded(count, template.MaxCount);
            var slots = Enumerable.Range(0, bag.ContainerSize)
                .Where(slot => bag.GetItemBySlot(slot) is null).Take(needed).ToArray();
            if (slots.Length != needed) return false;
            var committed = false;
            try
            {
                foreach (var slot in slots)
                {
                    var item = manager.Create(templateId, Math.Min(count, template.MaxCount), grade);
                    if (item is null) throw new InvalidOperationException("Item creation failed.");
                    planned.Add(item);
                    item.ExcludeFromWorldSave = true;
                    item.OwnerId = Id; item.SlotType = SlotType.Inventory; item.Slot = slot;
                    if (!bag.CanAccept(item, slot)) return false;
                    count -= item.Count;
                }
                using var connection = MySQL.CreateConnection();
                using var transaction = connection.BeginTransaction();
                foreach (var item in planned) AlphaRepository.SaveNewItem(connection, transaction, item, bag.ContainerId);
                if (grantAccessBy is { } actor) AlphaRepository.Grant(connection, transaction, Id, actor);
                transaction.Commit(); committed = true;
                foreach (var item in planned)
                {
                    item.ExcludeFromWorldSave = false;
                    if (!bag.AddOrMoveExistingItem(ItemTaskType.Invalid, item, item.Slot))
                        throw new InvalidOperationException("Durable alpha item could not attach to its reserved slot; relog required.");
                }
            }
            finally
            {
                if (!committed)
                    foreach (var item in planned) manager.ReleaseId(item.Id);
            }
        }
        // One normal Add task per stack avoids overflowing the native task-count field.
        foreach (var item in planned)
            SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.Gm, [new ItemAdd(item)], []));
        return true;
    }
}
