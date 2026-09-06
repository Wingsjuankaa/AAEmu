using Microsoft.Data.Sqlite;

namespace AAEmu.Game.Core.Managers;

internal static class QuestDoodadGroupCatalog
{
    internal static Dictionary<uint, HashSet<uint>> Load(SqliteConnection connection)
    {
        var groups = new Dictionary<uint, HashSet<uint>>();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT quest_doodad_group_id, doodad_id FROM quest_doodads";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var groupId = checked((uint)reader.GetInt64(0));
            var doodadId = checked((uint)reader.GetInt64(1));
            if (groupId == 0 || doodadId == 0)
                continue;
            if (!groups.TryGetValue(groupId, out var members))
                groups.Add(groupId, members = []);
            members.Add(doodadId);
        }
        return groups;
    }
}
