using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Char;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game.Items.Services;

internal static class EquipSlotReinforceRepository
{
    internal static void SaveState(MySqlConnection connection, MySqlTransaction transaction,
        uint owner, EquipSlotReinforceState state)
    {
        using var command = connection.CreateCommand(); command.Transaction = transaction;
        foreach (var (slot, value) in state.Slots)
        {
            command.CommandText = "INSERT INTO character_equip_slot_reinforces (owner,slot,level,experience) " +
                "VALUES (@owner,@slot,@level,@exp) ON DUPLICATE KEY UPDATE level=@level,experience=@exp";
            command.Parameters.AddWithValue("@owner", owner); command.Parameters.AddWithValue("@slot", slot);
            command.Parameters.AddWithValue("@level", value.Level); command.Parameters.AddWithValue("@exp", value.Experience);
            command.ExecuteNonQuery(); command.Parameters.Clear();
        }
        foreach (var (key, modifier) in state.Effects)
        {
            command.CommandText = "INSERT INTO character_equip_slot_reinforce_effects (owner,slot,level,modifier) " +
                "VALUES (@owner,@slot,@level,@modifier) ON DUPLICATE KEY UPDATE modifier=@modifier";
            command.Parameters.AddWithValue("@owner", owner); command.Parameters.AddWithValue("@slot", key.Slot);
            command.Parameters.AddWithValue("@level", key.Level); command.Parameters.AddWithValue("@modifier", modifier);
            command.ExecuteNonQuery(); command.Parameters.Clear();
        }
    }

    /// <summary>Writes the post-consumption item snapshot without changing the live item or dirty flag.
    /// Uses the same columns/details codec as ItemManager.Save, including not-yet-autosaved stacks.</summary>
    internal static void SaveConsumedItem(MySqlConnection connection, MySqlTransaction transaction,
        Item item, int amount)
    {
        if (amount <= 0 || item.Count < amount) throw new InvalidOperationException("Invalid Ipnya item snapshot.");
        using var command = connection.CreateCommand(); command.Transaction = transaction;
        command.Parameters.AddWithValue("@id", item.Id);
        if (item.Count == amount)
        {
            command.CommandText = "DELETE FROM items WHERE id=@id";
            command.ExecuteNonQuery(); return;
        }
        var details = new PacketStream(); item.WriteDetails(details);
        command.CommandText = "REPLACE INTO items " +
            "(id,type,template_id,container_id,slot_type,slot,count,details,lifespan_mins,made_unit_id," +
            "unsecure_time,unpack_time,owner,created_at,grade,flags,ucc,expire_time,expire_online_minutes,charge_time,charge_count) " +
            "VALUES (@id,@type,@template,@container,@slotType,@slot,@count,@details,@life,@made," +
            "@unsecure,@unpack,@owner,@created,@grade,@flags,@ucc,@expire,@online,@charge,@chargeCount)";
        command.Parameters.AddWithValue("@type", item.GetType().ToString());
        command.Parameters.AddWithValue("@template", item.TemplateId);
        command.Parameters.AddWithValue("@container", item._holdingContainer?.ContainerId ?? 0);
        command.Parameters.AddWithValue("@slotType", (int)item.SlotType); command.Parameters.AddWithValue("@slot", item.Slot);
        command.Parameters.AddWithValue("@count", item.Count - amount); command.Parameters.AddWithValue("@details", details.GetBytes());
        command.Parameters.AddWithValue("@life", item.LifespanMins); command.Parameters.AddWithValue("@made", item.MadeUnitId);
        command.Parameters.AddWithValue("@unsecure", item.UnsecureTime); command.Parameters.AddWithValue("@unpack", item.UnpackTime);
        command.Parameters.AddWithValue("@owner", item.OwnerId); command.Parameters.AddWithValue("@created", item.CreateTime);
        command.Parameters.AddWithValue("@grade", item.Grade); command.Parameters.AddWithValue("@flags", (byte)item.ItemFlags);
        command.Parameters.AddWithValue("@ucc", item.UccId); command.Parameters.AddWithValue("@expire", item.ExpirationTime);
        command.Parameters.AddWithValue("@online", item.ExpirationOnlineMinutesLeft); command.Parameters.AddWithValue("@charge", item.ChargeStartTime);
        command.Parameters.AddWithValue("@chargeCount", item.ChargeCount); command.ExecuteNonQuery();
    }
}
