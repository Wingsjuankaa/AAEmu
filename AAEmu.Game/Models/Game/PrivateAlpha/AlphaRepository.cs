using AAEmu.Commons.Network;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Models.Game.Items;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game.PrivateAlpha;

internal static class AlphaRepository
{
    internal static bool HasAccess(uint characterId)
    {
        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT 1 FROM private_alpha_access WHERE character_id=@id";
        command.Parameters.AddWithValue("@id", characterId);
        return command.ExecuteScalar() is not null;
    }
    internal static void Grant(MySqlConnection connection, MySqlTransaction transaction, uint id, uint actor)
    {
        using var command = connection.CreateCommand(); command.Transaction = transaction;
        command.CommandText = "INSERT INTO private_alpha_access (character_id,granted_by,granted_at) " +
            "VALUES (@id,@actor,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE granted_by=@actor,granted_at=UTC_TIMESTAMP()";
        command.Parameters.AddWithValue("@id", id); command.Parameters.AddWithValue("@actor", actor);
        command.ExecuteNonQuery();
    }
    internal static void Revoke(uint id)
    {
        using var connection = MySQL.CreateConnection(); using var command = connection.CreateCommand();
        command.CommandText = "DELETE FROM private_alpha_access WHERE character_id=@id";
        command.Parameters.AddWithValue("@id", id); command.ExecuteNonQuery();
    }
    internal static void SaveNewItem(MySqlConnection connection, MySqlTransaction transaction,
        Item item, ulong containerId)
    {
        using var command = connection.CreateCommand(); command.Transaction = transaction;
        command.Parameters.AddWithValue("@id", item.Id);
        var details = new PacketStream(); item.WriteDetails(details);
        command.CommandText = "INSERT INTO items " +
            "(id,type,template_id,container_id,slot_type,slot,count,details,lifespan_mins,made_unit_id," +
            "unsecure_time,unpack_time,owner,created_at,grade,flags,ucc,expire_time,expire_online_minutes,charge_time,charge_count) " +
            "VALUES (@id,@type,@template,@container,@slotType,@slot,@count,@details,@life,@made," +
            "@unsecure,@unpack,@owner,@created,@grade,@flags,@ucc,@expire,@online,@charge,@chargeCount)";
        command.Parameters.AddWithValue("@type", item.GetType().ToString());
        command.Parameters.AddWithValue("@template", item.TemplateId);
        command.Parameters.AddWithValue("@container", containerId);
        command.Parameters.AddWithValue("@slotType", (int)item.SlotType); command.Parameters.AddWithValue("@slot", item.Slot);
        command.Parameters.AddWithValue("@count", item.Count); command.Parameters.AddWithValue("@details", details.GetBytes());
        command.Parameters.AddWithValue("@life", item.LifespanMins); command.Parameters.AddWithValue("@made", item.MadeUnitId);
        command.Parameters.AddWithValue("@unsecure", item.UnsecureTime); command.Parameters.AddWithValue("@unpack", item.UnpackTime);
        command.Parameters.AddWithValue("@owner", item.OwnerId); command.Parameters.AddWithValue("@created", item.CreateTime);
        command.Parameters.AddWithValue("@grade", item.Grade); command.Parameters.AddWithValue("@flags", (byte)item.ItemFlags);
        command.Parameters.AddWithValue("@ucc", item.UccId); command.Parameters.AddWithValue("@expire", item.ExpirationTime);
        command.Parameters.AddWithValue("@online", item.ExpirationOnlineMinutesLeft); command.Parameters.AddWithValue("@charge", item.ChargeStartTime);
        command.Parameters.AddWithValue("@chargeCount", item.ChargeCount); command.ExecuteNonQuery();
    }
}
