using System.Collections.Concurrent;

using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.StaticValues;

using NLog;

namespace AAEmu.Game.Core.Managers;

/// <summary>Persistent AA10 social progression mutated by quest rewards.</summary>
public sealed class QuestRewardProgressManager : Singleton<QuestRewardProgressManager>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly ConcurrentDictionary<uint, LeadershipState> _leadership = new();

    public readonly record struct LeadershipState(uint Total, uint Daily, DateTime DailyDate);
    public readonly record struct ResidentSnapshot(uint PersonalPoint, uint MemberCount, uint ZonePoint,
        ulong NormalCharge, ulong HuntingCharge);

    public static uint CalculateSaturatedDelta(uint current, int requested) =>
        requested <= 0 ? 0 : (uint)Math.Min((ulong)(uint)requested, uint.MaxValue - (ulong)current);

    public static ulong CalculateSaturatedDelta(ulong current, int requested) =>
        requested <= 0 ? 0 : Math.Min((ulong)(uint)requested, ulong.MaxValue - current);

    public LeadershipState GetLeadershipState(uint characterId)
    {
        if (_leadership.TryGetValue(characterId, out var cached))
            return cached;

        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT leadership_point, daily_leadership_point, daily_reset_date FROM character_quest_reward_progress WHERE character_id=@character_id";
        command.Parameters.AddWithValue("@character_id", characterId);
        using var reader = command.ExecuteReader();
        var state = reader.Read()
            ? new LeadershipState(reader.GetUInt32("leadership_point"), reader.GetUInt32("daily_leadership_point"), reader.GetDateTime("daily_reset_date"))
            : new LeadershipState(0, 0, DateTime.UtcNow.Date);
        _leadership[characterId] = state;
        return state;
    }

    public bool TryAddLeadership(Character character, int point)
    {
        if (character is null || point < 0)
            return false;
        if (point == 0)
            return true;

        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        try
        {
            EnsureCharacterRow(connection, transaction, character.Id);
            uint total;
            uint daily;
            DateTime resetDate;
            using (var select = connection.CreateCommand())
            {
                select.Transaction = transaction;
                select.CommandText =
                    "SELECT leadership_point, daily_leadership_point, daily_reset_date FROM character_quest_reward_progress WHERE character_id=@character_id FOR UPDATE";
                select.Parameters.AddWithValue("@character_id", character.Id);
                using var reader = select.ExecuteReader();
                if (!reader.Read())
                    return false;
                total = reader.GetUInt32("leadership_point");
                daily = reader.GetUInt32("daily_leadership_point");
                resetDate = reader.GetDateTime("daily_reset_date");
            }

            var today = DateTime.UtcNow.Date;
            if (resetDate.Date != today)
                daily = 0;
            var applied = CalculateSaturatedDelta(total, point);
            var dailyApplied = CalculateSaturatedDelta(daily, (int)Math.Min(applied, int.MaxValue));
            total += applied;
            daily += dailyApplied;

            using (var update = connection.CreateCommand())
            {
                update.Transaction = transaction;
                update.CommandText =
                    "UPDATE character_quest_reward_progress SET leadership_point=@total, daily_leadership_point=@daily, daily_reset_date=@date WHERE character_id=@character_id";
                update.Parameters.AddWithValue("@total", total);
                update.Parameters.AddWithValue("@daily", daily);
                update.Parameters.AddWithValue("@date", today);
                update.Parameters.AddWithValue("@character_id", character.Id);
                if (update.ExecuteNonQuery() != 1)
                    return false;
            }
            transaction.Commit();
            _leadership[character.Id] = new LeadershipState(total, daily, today);
            character.SendPacket(new SCCharacterStatePacket(character));
            return true;
        }
        catch (Exception ex)
        {
            transaction.Rollback();
            Logger.Error(ex, "Failed to grant leadership points to character {0}", character.Id);
            return false;
        }
    }

    public bool TryAddFamilyExp(Character character, int point)
        => FamilyManager.Instance.TryAddExperience(character, point);

    public bool CanAddFamilyExp(Character character, int point) =>
        FamilyManager.Instance.CanAddExperience(character, point);

    public bool TryAddExpeditionExp(Character character, int point)
    {
        if (character?.Expedition is null || point < 0)
            return false;
        if (point == 0)
            return true;

        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        try
        {
            var expeditionId = (uint)character.Expedition.Id;
            using (var insert = connection.CreateCommand())
            {
                insert.Transaction = transaction;
                insert.CommandText =
                    "INSERT IGNORE INTO expedition_quest_progress(expedition_id, daily_reset_date) VALUES (@id, UTC_DATE())";
                insert.Parameters.AddWithValue("@id", expeditionId);
                insert.ExecuteNonQuery();
            }

            ulong exp;
            uint dailyExp;
            DateTime resetDate;
            using (var select = connection.CreateCommand())
            {
                select.Transaction = transaction;
                select.CommandText =
                    "SELECT exp, daily_exp, daily_reset_date FROM expedition_quest_progress WHERE expedition_id=@id FOR UPDATE";
                select.Parameters.AddWithValue("@id", expeditionId);
                using var reader = select.ExecuteReader();
                if (!reader.Read())
                    return false;
                exp = reader.GetUInt64("exp");
                dailyExp = reader.GetUInt32("daily_exp");
                resetDate = reader.GetDateTime("daily_reset_date");
            }

            var today = DateTime.UtcNow.Date;
            if (resetDate.Date != today)
                dailyExp = 0;
            var dailyCap = QuestManager.Instance.GetExpeditionLevel(exp).DailyExp;
            var remaining = dailyCap == 0 ? (uint)point : dailyCap > dailyExp ? dailyCap - dailyExp : 0;
            var applied = Math.Min((uint)point, remaining);
            var newExp = exp + applied < exp ? ulong.MaxValue : exp + applied;
            var newDailyExp = (uint)Math.Min((ulong)dailyExp + applied, uint.MaxValue);

            using (var update = connection.CreateCommand())
            {
                update.Transaction = transaction;
                update.CommandText =
                    "UPDATE expedition_quest_progress SET exp=@exp, daily_exp=@daily, daily_reset_date=@date WHERE expedition_id=@id";
                update.Parameters.AddWithValue("@exp", newExp);
                update.Parameters.AddWithValue("@daily", newDailyExp);
                update.Parameters.AddWithValue("@date", today);
                update.Parameters.AddWithValue("@id", expeditionId);
                if (update.ExecuteNonQuery() != 1)
                    return false;
            }
            transaction.Commit();
            if (applied > 0)
                character.Expedition.SendPacket(new SCExpeditionExpAddPacket(applied));
            return true;
        }
        catch (Exception ex)
        {
            transaction.Rollback();
            Logger.Error(ex, "Failed to grant expedition exp to expedition {0}", character.Expedition.Id);
            return false;
        }
    }

    public bool TryAddResidentPoint(Character character, uint zoneGroupId, int point)
    {
        if (!CanAddResidentPoint(character, zoneGroupId, point))
            return false;
        if (point == 0)
        {
            SendResidentInfo(character, zoneGroupId);
            return true;
        }

        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        try
        {
            EnsureResidentPointRow(connection, transaction, character.Id, zoneGroupId);
            uint current;
            using (var select = connection.CreateCommand())
            {
                select.Transaction = transaction;
                select.CommandText = @"SELECT service_point FROM resident_service_points
WHERE character_id=@character_id AND zone_group_id=@zone_group_id FOR UPDATE";
                select.Parameters.AddWithValue("@character_id", character.Id);
                select.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
                using var reader = select.ExecuteReader();
                if (!reader.Read())
                    return false;
                current = reader.GetUInt32("service_point");
            }

            var applied = CalculateSaturatedDelta(current, point);
            using (var update = connection.CreateCommand())
            {
                update.Transaction = transaction;
                update.CommandText = @"UPDATE resident_service_points SET service_point=@point, updated_at=UTC_TIMESTAMP()
WHERE character_id=@character_id AND zone_group_id=@zone_group_id";
                update.Parameters.AddWithValue("@point", current + applied);
                update.Parameters.AddWithValue("@character_id", character.Id);
                update.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
                if (update.ExecuteNonQuery() != 1)
                    return false;
            }
            transaction.Commit();
            SendResidentInfo(character, zoneGroupId);
            return true;
        }
        catch (Exception ex)
        {
            transaction.Rollback();
            Logger.Error(ex, "Failed to grant resident points to character {0}, zone {1}", character.Id, zoneGroupId);
            return false;
        }
    }

    public bool CanAddResidentPoint(Character character, uint zoneGroupId, int point) =>
        character is not null && IsValidResidentZone(zoneGroupId) && point >= 0;

    public bool TryAddResidentCharge(Character character, uint zoneGroupId, int charge)
    {
        if (!CanAddResidentCharge(character, zoneGroupId, charge))
            return false;
        if (charge == 0)
        {
            SendResidentInfo(character, zoneGroupId);
            return true;
        }

        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        try
        {
            EnsureResidentBalanceRow(connection, transaction, zoneGroupId);
            ulong current;
            using (var select = connection.CreateCommand())
            {
                select.Transaction = transaction;
                select.CommandText =
                    "SELECT normal_charge FROM resident_zone_balances WHERE zone_group_id=@zone_group_id FOR UPDATE";
                select.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
                using var reader = select.ExecuteReader();
                if (!reader.Read())
                    return false;
                current = reader.GetUInt64("normal_charge");
            }

            var applied = CalculateSaturatedDelta(current, charge);
            using (var update = connection.CreateCommand())
            {
                update.Transaction = transaction;
                update.CommandText = @"UPDATE resident_zone_balances SET normal_charge=@charge, updated_at=UTC_TIMESTAMP()
WHERE zone_group_id=@zone_group_id";
                update.Parameters.AddWithValue("@charge", current + applied);
                update.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
                if (update.ExecuteNonQuery() != 1)
                    return false;
            }
            transaction.Commit();
            SendResidentInfo(character, zoneGroupId);
            return true;
        }
        catch (Exception ex)
        {
            transaction.Rollback();
            Logger.Error(ex, "Failed to grant resident charge for zone {0}", zoneGroupId);
            return false;
        }
    }

    public bool CanAddResidentCharge(Character character, uint zoneGroupId, int charge) =>
        character is not null && IsValidResidentZone(zoneGroupId) && charge >= 0;

    public bool TryChangeFaction(Character character, uint systemFactionId, bool ignoreLimit, bool inferiorEscape)
    {
        if (!TryResolveFactionTarget(character, systemFactionId, out var target))
            return false;

        if (character.Faction?.Id == target.Id)
            return true;

        var targetRoot = ResolveFactionRoot(target.Id, target.MotherId);
        if (character.Expedition != null)
        {
            var expeditionFaction = FactionManager.Instance.GetFaction(character.Expedition.MotherId);
            var expeditionRoot = expeditionFaction == null
                ? character.Expedition.MotherId
                : ResolveFactionRoot(expeditionFaction.Id, expeditionFaction.MotherId);
            if (ShouldLeaveExpedition(expeditionRoot, targetRoot))
                ExpeditionManager.Leave(character);
        }

        Logger.Info(
            "Applying authored faction-change reward for {0}: target={1}, ignoreLimit={2}, inferiorEscape={3}",
            character.Id, target.Id, ignoreLimit, inferiorEscape);
        character.SetFaction(target.Id);
        HousingManager.Instance.UpdateOwnedHousingFaction(character.Id, target.Id);
        foreach (var doodad in character.ParentWorld?.SpawnManager?.GetPlayerDoodads(character.Id) ?? [])
            DoodadManager.Instance.RefreshFaction(doodad, character, doodad.ParentObj as House);
        return true;
    }

    public bool CanChangeFaction(Character character, uint systemFactionId) =>
        TryResolveFactionTarget(character, systemFactionId, out _);

    public static FactionsEnum ResolveFactionRoot(FactionsEnum id, FactionsEnum motherId) =>
        motherId != FactionsEnum.Invalid ? motherId : id;

    public static bool ShouldLeaveExpedition(FactionsEnum expeditionMotherId, FactionsEnum targetRoot) =>
        expeditionMotherId != targetRoot;

    private static bool TryResolveFactionTarget(Character character, uint systemFactionId,
        out Models.Game.Faction.SystemFaction target)
    {
        target = null;
        if (character is null)
            return false;

        var targetId = systemFactionId == 0
            ? CharacterManager.Instance.GetTemplate(character.Race, character.Gender).FactionId
            : (FactionsEnum)systemFactionId;
        target = FactionManager.Instance.GetFaction(targetId);
        return target != null;
    }

    public void SendResidentInfo(Character character, uint zoneGroupId)
    {
        if (character is null || !IsValidResidentZone(zoneGroupId))
            return;
        var state = GetResidentSnapshot(character.Id, zoneGroupId);
        character.SendPacket(new SCResidentInfoPacket((short)zoneGroupId, character.Id, state.PersonalPoint));
        character.SendPacket(new SCResidentBalanceInfoPacket((short)zoneGroupId, character.Id,
            state.MemberCount, state.PersonalPoint, state.ZonePoint, state.NormalCharge, state.HuntingCharge));
    }

    public ResidentSnapshot GetResidentSnapshot(uint characterId, uint zoneGroupId)
    {
        if (!IsValidResidentZone(zoneGroupId))
            return default;

        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText = @"SELECT
COALESCE(MAX(CASE WHEN character_id=@character_id THEN service_point END), 0) AS personal_point,
COUNT(CASE WHEN service_point > 0 THEN 1 END) AS member_count,
COALESCE(SUM(service_point), 0) AS zone_point,
COALESCE((SELECT normal_charge FROM resident_zone_balances WHERE zone_group_id=@zone_group_id), 0) AS normal_charge,
COALESCE((SELECT hunting_charge FROM resident_zone_balances WHERE zone_group_id=@zone_group_id), 0) AS hunting_charge
FROM resident_service_points WHERE zone_group_id=@zone_group_id";
        command.Parameters.AddWithValue("@character_id", characterId);
        command.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
        using var reader = command.ExecuteReader();
        if (!reader.Read())
            return default;
        return new ResidentSnapshot(
            Convert.ToUInt32(reader["personal_point"]),
            Convert.ToUInt32(reader["member_count"]),
            (uint)Math.Min(Convert.ToUInt64(reader["zone_point"]), uint.MaxValue),
            Convert.ToUInt64(reader["normal_charge"]),
            Convert.ToUInt64(reader["hunting_charge"]));
    }

    private static bool IsValidResidentZone(uint zoneGroupId) => zoneGroupId > 0 && zoneGroupId <= (uint)short.MaxValue;

    private static void EnsureResidentPointRow(MySql.Data.MySqlClient.MySqlConnection connection,
        MySql.Data.MySqlClient.MySqlTransaction transaction, uint characterId, uint zoneGroupId)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = @"INSERT IGNORE INTO resident_service_points
(character_id, zone_group_id, service_point, updated_at) VALUES (@character_id, @zone_group_id, 0, UTC_TIMESTAMP())";
        command.Parameters.AddWithValue("@character_id", characterId);
        command.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
        command.ExecuteNonQuery();
    }

    private static void EnsureResidentBalanceRow(MySql.Data.MySqlClient.MySqlConnection connection,
        MySql.Data.MySqlClient.MySqlTransaction transaction, uint zoneGroupId)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = @"INSERT IGNORE INTO resident_zone_balances
(zone_group_id, normal_charge, hunting_charge, updated_at) VALUES (@zone_group_id, 0, 0, UTC_TIMESTAMP())";
        command.Parameters.AddWithValue("@zone_group_id", zoneGroupId);
        command.ExecuteNonQuery();
    }

    private static void EnsureCharacterRow(MySql.Data.MySqlClient.MySqlConnection connection,
        MySql.Data.MySqlClient.MySqlTransaction transaction, uint characterId)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText =
            "INSERT IGNORE INTO character_quest_reward_progress(character_id, daily_reset_date) VALUES (@character_id, UTC_DATE())";
        command.Parameters.AddWithValue("@character_id", characterId);
        command.ExecuteNonQuery();
    }

}
