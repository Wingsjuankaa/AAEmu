using AAEmu.Game.Core.Packets.G2C;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>Per-character AA10 Loot Gacha counters used by advanced-pack pity rules.</summary>
public sealed class CharacterGachaRecords(Character owner)
{
    private readonly object _sync = new();
    private readonly Dictionary<uint, uint> _totalCounts = [];
    private readonly Dictionary<uint, uint> _lastRounds = [];

    public void Load(MySqlConnection connection)
    {
        lock (_sync)
        {
            _totalCounts.Clear();
            _lastRounds.Clear();

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT gacha_loot_pack_id, total_count FROM character_gacha_records WHERE owner = @owner";
                command.Parameters.AddWithValue("@owner", owner.Id);
                using var reader = command.ExecuteReader();
                while (reader.Read())
                    _totalCounts[reader.GetUInt32("gacha_loot_pack_id")] =
                        reader.GetUInt32("total_count");
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT gacha_advanced_loot_pack_id, last_round FROM character_gacha_advanced_records " +
                    "WHERE owner = @owner";
                command.Parameters.AddWithValue("@owner", owner.Id);
                using var reader = command.ExecuteReader();
                while (reader.Read())
                    _lastRounds[reader.GetUInt32("gacha_advanced_loot_pack_id")] =
                        reader.GetUInt32("last_round");
            }
        }
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        lock (_sync)
        {
            foreach (var (packId, totalCount) in _totalCounts)
            {
                using var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText =
                    "REPLACE INTO character_gacha_records (owner, gacha_loot_pack_id, total_count) " +
                    "VALUES (@owner, @pack, @count)";
                command.Parameters.AddWithValue("@owner", owner.Id);
                command.Parameters.AddWithValue("@pack", packId);
                command.Parameters.AddWithValue("@count", totalCount);
                command.ExecuteNonQuery();
            }

            foreach (var (advancedId, lastRound) in _lastRounds)
            {
                using var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText =
                    "REPLACE INTO character_gacha_advanced_records " +
                    "(owner, gacha_advanced_loot_pack_id, last_round) VALUES (@owner, @advanced, @round)";
                command.Parameters.AddWithValue("@owner", owner.Id);
                command.Parameters.AddWithValue("@advanced", advancedId);
                command.Parameters.AddWithValue("@round", lastRound);
                command.ExecuteNonQuery();
            }
        }
    }

    public (uint TotalCount, IReadOnlyDictionary<uint, uint> LastRounds) Snapshot(uint packId)
    {
        lock (_sync)
            return (_totalCounts.GetValueOrDefault(packId),
                new Dictionary<uint, uint>(_lastRounds));
    }

    public void Commit(uint packId, uint totalCount, IReadOnlyDictionary<uint, uint> updatedLastRounds)
    {
        lock (_sync)
        {
            _totalCounts[packId] = totalCount;
            foreach (var (advancedId, lastRound) in updatedLastRounds)
                _lastRounds[advancedId] = lastRound;
        }
    }

    public SCDumpGachaRecordPacket CreateDumpPacket(uint packId)
    {
        lock (_sync)
        {
            var rows = _lastRounds
                .OrderBy(entry => entry.Key)
                .Select(entry => new GachaAdvancedRecordEntry(entry.Key, entry.Value))
                .ToArray();
            return new SCDumpGachaRecordPacket(packId, _totalCounts.GetValueOrDefault(packId), rows);
        }
    }
}
