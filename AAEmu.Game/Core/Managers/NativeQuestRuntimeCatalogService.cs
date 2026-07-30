using System.Collections.Generic;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Observations;
using AAEmu.Game.Utils.DB;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    /// <summary>
    /// Read-only view of the strict AA8 quest catalog embedded in compact.
    /// It explains quarantined requests without making observations authoritative.
    /// </summary>
    public sealed class NativeQuestRuntimeCatalogService :
        Singleton<NativeQuestRuntimeCatalogService>
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly Dictionary<uint, NativeQuestRuntimeEntry> _entries =
            new Dictionary<uint, NativeQuestRuntimeEntry>();

        public bool Available { get; private set; }
        public int Count => _entries.Count;

        public void Load()
        {
            _entries.Clear();
            Available = false;

            using (var connection = SQLite.CreateConnection())
            {
                if (connection == null)
                    return;
                using (var command = connection.CreateCommand())
                {
                    command.CommandText =
                        "SELECT quest_id,state,reasons_json,act_types_json," +
                        "item_ids_json,npc_ids_json,doodad_ids_json,authority " +
                        "FROM aaemu_native_quest_runtime_catalog";
                    try
                    {
                        using (var reader = command.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                var entry = new NativeQuestRuntimeEntry
                                {
                                    QuestId = (uint)reader.GetInt64(0),
                                    State = reader.GetString(1),
                                    ReasonsJson = reader.GetString(2),
                                    ActTypesJson = reader.GetString(3),
                                    ItemIdsJson = reader.GetString(4),
                                    NpcIdsJson = reader.GetString(5),
                                    DoodadIdsJson = reader.GetString(6),
                                    Authority = reader.GetString(7)
                                };
                                _entries[entry.QuestId] = entry;
                            }
                        }
                    }
                    catch (Microsoft.Data.Sqlite.SqliteException ex)
                    {
                        Log.Warn(
                            ex,
                            "[AA8Observation] Native quest runtime catalog is unavailable.");
                        return;
                    }
                }
            }

            Available = _entries.Count > 0;
            Log.Info(
                "[AA8Observation] Loaded {0} native quest catalog classifications.",
                _entries.Count);
        }

        public NativeQuestRuntimeEntry Get(uint questId)
        {
            return _entries.TryGetValue(questId, out var entry)
                ? entry
                : new NativeQuestRuntimeEntry { QuestId = questId };
        }
    }
}
