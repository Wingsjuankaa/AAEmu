using System.Collections.Concurrent;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items.Actions;
using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Core.Managers;

/// <summary>Account-scoped, once-per-UTC-day attendance claims for the active monthly campaign.</summary>
public class AccountAttendanceManager : Singleton<AccountAttendanceManager>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly ConcurrentDictionary<uint, object> _accountLocks = new();

    public void SendState(Character character)
    {
        if (character is null || !IsEnabled())
            return;

        var now = ServerCalendar.UtcNow;
        var campaign = AccountAttendanceGameData.Instance.GetCampaign(now.Year, now.Month);
        if (campaign.Count == 0)
        {
            character.SendPacket(new SCAccountAttendancePacket());
            return;
        }

        var claims = LoadClaims(character.AccountId, now.Year, now.Month);
        character.SendPacket(BuildStatePacket(claims));
    }

    public void Claim(Character character, ulong clientType, uint clientDayOffset)
    {
        if (character is null || !IsEnabled())
            return;

        lock (_accountLocks.GetOrAdd(character.AccountId, _ => new object()))
        {
            var now = ServerCalendar.UtcNow;
            var campaign = AccountAttendanceGameData.Instance.GetCampaign(now.Year, now.Month);
            var dailyRewardCount = campaign.Count(reward => !reward.AdditionalReward);
            if (dailyRewardCount == 0)
            {
                Reject(character, "there is no active campaign");
                return;
            }

            var claims = LoadClaims(character.AccountId, now.Year, now.Month);
            if (claims.Any(claim => claim.ClaimDay == now.Date))
            {
                Reject(character, "today was already claimed");
                return;
            }

            var nextDayCount = claims.Count + 1;
            var rewardRows = AccountAttendanceGameData.Instance
                .GetRewardsForClaim(now.Year, now.Month, nextDayCount);
            if (nextDayCount > dailyRewardCount || rewardRows.Count == 0 ||
                rewardRows.All(reward => reward.AdditionalReward))
            {
                Reject(character, $"claim index {nextDayCount} is outside the campaign");
                return;
            }

            var rewards = rewardRows
                .Select(reward => (reward.ItemId, reward.ItemCount, reward.ItemGradeId))
                .ToArray();
            var bag = character.Inventory.Bag;
            if (!bag.CanAcquireDefaultItems(rewards))
            {
                Reject(character, "the bag cannot hold all rewards");
                return;
            }

            if (!TryPersistClaim(character, now, nextDayCount))
            {
                Reject(character, "the claim lost an idempotency race");
                return;
            }

            var itemTasks = new List<ItemTask>();
            if (!bag.TryAcquireDefaultItemsIntoTaskBatch(rewards, itemTasks))
            {
                DeleteClaim(character.AccountId, now.Year, now.Month, nextDayCount);
                Reject(character, "the preflighted reward could not be acquired");
                return;
            }

            foreach (var itemTask in itemTasks)
                character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.TodReward, itemTask, []));

            var unixTime = Helpers.UnixTime(now);
            character.SendPacket(new SCAccountAttendanceAddedPacket(true, unixTime, false));
            claims.Add(new AttendanceClaim(nextDayCount, now, now.Date, false));
            character.SendPacket(BuildStatePacket(claims));

            Logger.Info(
                "Account Attendance claimed: account={0}, character={1}/{2}, campaign={3:D4}-{4:D2}, " +
                "dayCount={5}, rewards={6}, clientType={7}, clientDayOffset={8}",
                character.AccountId, character.Name, character.Id, now.Year, now.Month,
                nextDayCount,
                string.Join(",", rewardRows.Select(row => $"{row.ItemId}x{row.ItemCount}@{row.ItemGradeId}")),
                clientType, clientDayOffset);
        }
    }

    private static bool IsEnabled() =>
        FeaturesManager.Fsets?.Check(Feature.account_attendance) == true;

    private static SCAccountAttendancePacket BuildStatePacket(IReadOnlyCollection<AttendanceClaim> claims)
    {
        var times = new long[SCAccountAttendancePacket.Days];
        var archelife = new bool[SCAccountAttendancePacket.Days];
        foreach (var claim in claims.Where(claim => claim.DayCount is >= 1 and <= SCAccountAttendancePacket.Days))
        {
            var index = claim.DayCount - 1;
            times[index] = Helpers.UnixTime(ServerCalendar.AsUtc(claim.ClaimedAt));
            archelife[index] = claim.IsArchelife;
        }
        return new SCAccountAttendancePacket(times, archelife);
    }

    private static List<AttendanceClaim> LoadClaims(uint accountId, int year, int month)
    {
        var result = new List<AttendanceClaim>();
        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT day_count, claimed_at, claim_day, is_archelife
            FROM account_attendance_claims
            WHERE account_id = @account_id AND campaign_year = @year AND campaign_month = @month
            ORDER BY day_count
            """;
        command.Parameters.AddWithValue("@account_id", accountId);
        command.Parameters.AddWithValue("@year", year);
        command.Parameters.AddWithValue("@month", month);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            result.Add(new AttendanceClaim(
                reader.GetInt32("day_count"),
                ServerCalendar.AsUtc(reader.GetDateTime("claimed_at")),
                reader.GetDateTime("claim_day").Date,
                reader.GetBoolean("is_archelife")));
        }
        return result;
    }

    private static bool TryPersistClaim(Character character, DateTime now, int dayCount)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText = """
                INSERT INTO account_attendance_claims
                    (account_id, campaign_year, campaign_month, day_count, claim_day,
                     claimed_at, is_archelife, claimed_by)
                VALUES
                    (@account_id, @year, @month, @day_count, @claim_day,
                     @claimed_at, 0, @claimed_by)
                """;
            command.Parameters.AddWithValue("@account_id", character.AccountId);
            command.Parameters.AddWithValue("@year", now.Year);
            command.Parameters.AddWithValue("@month", now.Month);
            command.Parameters.AddWithValue("@day_count", dayCount);
            command.Parameters.AddWithValue("@claim_day", now.Date);
            command.Parameters.AddWithValue("@claimed_at", now);
            command.Parameters.AddWithValue("@claimed_by", character.Id);
            return command.ExecuteNonQuery() == 1;
        }
        catch (MySqlException exception) when (exception.Number == 1062)
        {
            return false;
        }
    }

    private static void DeleteClaim(uint accountId, int year, int month, int dayCount)
    {
        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText = """
            DELETE FROM account_attendance_claims
            WHERE account_id = @account_id AND campaign_year = @year
              AND campaign_month = @month AND day_count = @day_count
            """;
        command.Parameters.AddWithValue("@account_id", accountId);
        command.Parameters.AddWithValue("@year", year);
        command.Parameters.AddWithValue("@month", month);
        command.Parameters.AddWithValue("@day_count", dayCount);
        command.ExecuteNonQuery();
    }

    private static void Reject(Character character, string reason)
    {
        Logger.Warn("Account Attendance rejected for {0}/{1}: {2}", character.Name, character.AccountId, reason);
        character.SendPacket(new SCAccountAttendanceAddedPacket(false, 0, false));
        SendCurrentState(character);
    }

    private static void SendCurrentState(Character character)
    {
        var now = ServerCalendar.UtcNow;
        character.SendPacket(BuildStatePacket(LoadClaims(character.AccountId, now.Year, now.Month)));
    }

    private sealed record AttendanceClaim(int DayCount, DateTime ClaimedAt, DateTime ClaimDay, bool IsArchelife);
}
