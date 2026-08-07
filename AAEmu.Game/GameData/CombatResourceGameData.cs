using System.Collections.Generic;

using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData
{
    public class CombatResourceDefinition
    {
        public uint Id { get; set; }
        public string Name { get; set; }
        public int Max { get; set; }
        public int DefaultPoint { get; set; }
        public uint BuffId { get; set; }
        public int ResourceBuffConditionId { get; set; }
        public int RecoveryCycle { get; set; }
        public int PeaceRecoveryAmount { get; set; }
        public int CombatRecoveryAmount { get; set; }
        public int EtcRecoveryStateId { get; set; }
        public int EtcRecoveryAmount { get; set; }
        public int SendTypeId { get; set; }
    }

    public class CombatResourceGroupDefinition
    {
        public uint Id { get; set; }
        public AbilityType AbilityId { get; set; }
        public uint PrimaryResourceId { get; set; }
        public uint SecondaryResourceId { get; set; }
        public bool ShowUpdateTime { get; set; }
        public bool ShowTransformUpdateTime { get; set; }
    }

    /// <summary>
    /// AA8 combat-resource descriptors. Resource points are kept in logical units
    /// server-side; the AA8 wire protocol converts them to hundredths.
    /// </summary>
    [GameData]
    public class CombatResourceGameData : Singleton<CombatResourceGameData>, IGameDataLoader
    {
        private Dictionary<uint, CombatResourceDefinition> _resources =
            new Dictionary<uint, CombatResourceDefinition>();
        private Dictionary<AbilityType, CombatResourceGroupDefinition> _groupsByAbility =
            new Dictionary<AbilityType, CombatResourceGroupDefinition>();

        public void Load(SqliteConnection connection)
        {
            _resources = new Dictionary<uint, CombatResourceDefinition>();
            _groupsByAbility = new Dictionary<AbilityType, CombatResourceGroupDefinition>();

            if (!TableExists(connection, "combat_resources"))
                return;

            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM combat_resources";
                command.Prepare();
                using (var sqliteReader = command.ExecuteReader())
                using (var reader = new SQLiteWrapperReader(sqliteReader))
                {
                    while (reader.Read())
                    {
                        var definition = new CombatResourceDefinition
                        {
                            Id = reader.GetUInt32("id"),
                            Name = reader.GetStringOrDefault("name", string.Empty),
                            Max = reader.GetInt32OrDefault("max", 0),
                            DefaultPoint = reader.GetInt32OrDefault("default_point", 0),
                            BuffId = reader.GetUInt32OrDefault("buff_id", 0),
                            ResourceBuffConditionId = reader.GetInt32OrDefault("resource_buff_condition_id", 1),
                            RecoveryCycle = reader.GetInt32OrDefault("recovery_cycle", 0),
                            PeaceRecoveryAmount = reader.GetInt32OrDefault("peace_recovery_amount", 0),
                            CombatRecoveryAmount = reader.GetInt32OrDefault("combat_recovery_amount", 0),
                            EtcRecoveryStateId = reader.GetInt32OrDefault("etc_recovery_state_id", 0),
                            EtcRecoveryAmount = reader.GetInt32OrDefault("etc_recovery_amount", 0),
                            // The misspelling is part of the retail schema.
                            SendTypeId = reader.GetInt32OrDefault("resouece_send_type_id", 1)
                        };
                        _resources[definition.Id] = definition;
                    }
                }
            }

            if (!TableExists(connection, "combat_resource_groups"))
                return;

            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM combat_resource_groups";
                command.Prepare();
                using (var sqliteReader = command.ExecuteReader())
                using (var reader = new SQLiteWrapperReader(sqliteReader))
                {
                    while (reader.Read())
                    {
                        var definition = new CombatResourceGroupDefinition
                        {
                            Id = reader.GetUInt32("id"),
                            AbilityId = (AbilityType)reader.GetUInt32("ability_id"),
                            PrimaryResourceId = reader.GetUInt32OrDefault("combat_resource_1_id", 0),
                            SecondaryResourceId = reader.GetUInt32OrDefault("combat_resource_2_id", 0),
                            ShowUpdateTime = reader.GetBooleanOrDefault("show_update_time_combat_resource", false),
                            ShowTransformUpdateTime = reader.GetBooleanOrDefault(
                                "show_update_time_transform_combat_resource", false)
                        };
                        _groupsByAbility[definition.AbilityId] = definition;
                    }
                }
            }
        }

        public void PostLoad()
        {
        }

        public CombatResourceDefinition Get(uint id)
        {
            return _resources.TryGetValue(id, out var definition) ? definition : null;
        }

        public CombatResourceGroupDefinition GetGroup(AbilityType ability)
        {
            return _groupsByAbility.TryGetValue(ability, out var definition) ? definition : null;
        }

        public uint ResolvePrimaryResourceId(AbilityType ability)
        {
            return GetGroup(ability)?.PrimaryResourceId ?? 0;
        }

        private static bool TableExists(SqliteConnection connection, string tableName)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = $name LIMIT 1";
                command.Parameters.AddWithValue("$name", tableName);
                return command.ExecuteScalar() != null;
            }
        }
    }
}
