using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Attendance;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.GameData;

/// <summary>Loads the monthly Account Attendance reward catalog shipped by AA10.</summary>
[GameData]
public class AccountAttendanceGameData : Singleton<AccountAttendanceGameData>, IGameDataLoader
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private Dictionary<(int Year, int Month), List<AccountAttendanceReward>> _campaigns = [];

    public void Load(SqliteConnection connection)
    {
        _campaigns = [];
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT id, year, month, day_count, item_id, item_grade_id, item_count, additional_reward
            FROM account_attendance_rewards
            ORDER BY year, month, day_count, id
            """;
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);
        while (reader.Read())
        {
            var reward = new AccountAttendanceReward(
                reader.GetUInt32("id"),
                reader.GetInt32("year"),
                reader.GetInt32("month"),
                reader.GetInt32("day_count"),
                reader.GetUInt32("item_id"),
                reader.GetInt32("item_grade_id"),
                reader.GetInt32("item_count"),
                reader.GetBoolean("additional_reward"));
            var key = (reward.Year, reward.Month);
            if (!_campaigns.TryGetValue(key, out var rewards))
                _campaigns[key] = rewards = [];
            rewards.Add(reward);
        }

        Logger.Info("Loaded {0} Account Attendance campaigns ({1} reward rows)",
            _campaigns.Count, _campaigns.Values.Sum(rewards => rewards.Count));
    }

    public void PostLoad()
    {
    }

    public IReadOnlyList<AccountAttendanceReward> GetCampaign(int year, int month) =>
        _campaigns.GetValueOrDefault((year, month)) ?? [];

    public IReadOnlyList<AccountAttendanceReward> GetRewardsForClaim(int year, int month, int dayCount) =>
        GetCampaign(year, month)
            .Where(reward => reward.DayCount == dayCount)
            .OrderBy(reward => reward.AdditionalReward)
            .ThenBy(reward => reward.Id)
            .ToArray();
}
