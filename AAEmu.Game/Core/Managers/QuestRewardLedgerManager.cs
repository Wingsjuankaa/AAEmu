using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;

using NLog;

namespace AAEmu.Game.Core.Managers;

public enum QuestRewardLedgerState : byte
{
    Absent = 0,
    Pending = 1,
    Completed = 2,
    Conflict = 3,
    Unavailable = 4
}

public enum QuestRewardCompletionMode : byte
{
    Immediate = 0,
    AfterPersistence = 1
}

public readonly record struct QuestRewardLedgerKey(
    Guid AttemptId,
    uint ActId,
    uint CharacterId,
    uint QuestTemplateId,
    string DetailType,
    uint DetailId);

/// <summary>
/// Durable, fail-closed idempotency boundary for AA10 quest reward acts.
/// A crash after the domain mutation and before ledger completion intentionally
/// leaves Pending for operator reconciliation instead of guessing and granting
/// the reward twice.
/// </summary>
public sealed class QuestRewardLedgerManager : Singleton<QuestRewardLedgerManager>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    public static bool CanProceed(QuestRewardLedgerState state, bool semanticPreflight) => state switch
    {
        QuestRewardLedgerState.Completed => true,
        QuestRewardLedgerState.Absent => semanticPreflight,
        _ => false
    };

    public bool CanExecute(Quest quest, QuestAct questAct, Func<bool> semanticPreflight)
    {
        if (!TryCreateKey(quest, questAct, out var key))
            return false;

        var state = Inspect(key);
        if (state == QuestRewardLedgerState.Completed)
            return true;
        if (state != QuestRewardLedgerState.Absent)
        {
            LogBlocked(key, state);
            return false;
        }

        return semanticPreflight();
    }

    public bool TryExecute(Quest quest, QuestAct questAct, Func<bool> mutation,
        QuestRewardCompletionMode completionMode)
    {
        if (!TryCreateKey(quest, questAct, out var key))
            return false;

        var reservation = Reserve(key);
        if (reservation == QuestRewardLedgerState.Completed)
            return true;
        if (reservation != QuestRewardLedgerState.Pending)
        {
            LogBlocked(key, reservation);
            return false;
        }

        bool applied;
        try
        {
            applied = mutation();
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Quest reward mutation failed for attempt {0}, act {1}", key.AttemptId, key.ActId);
            applied = false;
        }

        if (!applied)
        {
            Release(key);
            return false;
        }

        if (completionMode == QuestRewardCompletionMode.AfterPersistence)
        {
            quest.TrackDeferredRewardAct(key);
            return true;
        }

        return Complete(key);
    }

    public bool Complete(QuestRewardLedgerKey key)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText =
                "UPDATE quest_reward_ledger SET status=1, completed_at=UTC_TIMESTAMP() " +
                "WHERE attempt_id=@attempt_id AND act_id=@act_id AND status=0";
            AddKeyParameters(command, key);
            if (command.ExecuteNonQuery() == 1)
                return true;

            return Inspect(key) == QuestRewardLedgerState.Completed;
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Could not complete quest reward ledger attempt {0}, act {1}; it remains pending",
                key.AttemptId, key.ActId);
            return false;
        }
    }

    /// <summary>
    /// Enlists ledger completion in the SaveManager transaction that persists
    /// mails, items, character state, and quest removal. Returns true only when
    /// the row was already completed by an earlier committed save, allowing the
    /// caller to discard its retry marker safely.
    /// </summary>
    public bool CompleteWithinSave(MySql.Data.MySqlClient.MySqlConnection connection,
        MySql.Data.MySqlClient.MySqlTransaction transaction, QuestRewardLedgerKey key)
    {
        using (var update = connection.CreateCommand())
        {
            update.Transaction = transaction;
            update.CommandText =
                "UPDATE quest_reward_ledger SET status=1, completed_at=UTC_TIMESTAMP() " +
                "WHERE attempt_id=@attempt_id AND act_id=@act_id AND status=0";
            AddKeyParameters(update, key);
            if (update.ExecuteNonQuery() == 1)
                return false; // Keep one save cycle so an outer rollback retries it.
        }

        using var select = connection.CreateCommand();
        select.Transaction = transaction;
        select.CommandText =
            "SELECT status FROM quest_reward_ledger WHERE attempt_id=@attempt_id AND act_id=@act_id";
        AddKeyParameters(select, key);
        var value = select.ExecuteScalar();
        if (value is not null && Convert.ToByte(value) == 1)
            return true;
        throw new InvalidOperationException(
            $"Quest reward ledger row {key.AttemptId}/{key.ActId} disappeared before save completion");
    }

    private QuestRewardLedgerState Inspect(QuestRewardLedgerKey key)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText =
                "SELECT character_id, quest_template_id, detail_type, detail_id, status " +
                "FROM quest_reward_ledger WHERE attempt_id=@attempt_id AND act_id=@act_id";
            AddKeyParameters(command, key);
            using var reader = command.ExecuteReader();
            if (!reader.Read())
                return QuestRewardLedgerState.Absent;

            if (reader.GetUInt32("character_id") != key.CharacterId ||
                reader.GetUInt32("quest_template_id") != key.QuestTemplateId ||
                reader.GetString("detail_type") != key.DetailType ||
                reader.GetUInt32("detail_id") != key.DetailId)
                return QuestRewardLedgerState.Conflict;

            return reader.GetByte("status") == 1
                ? QuestRewardLedgerState.Completed
                : QuestRewardLedgerState.Pending;
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Quest reward ledger unavailable for attempt {0}, act {1}", key.AttemptId, key.ActId);
            return QuestRewardLedgerState.Unavailable;
        }
    }

    private QuestRewardLedgerState Reserve(QuestRewardLedgerKey key)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText =
                "INSERT IGNORE INTO quest_reward_ledger " +
                "(attempt_id, act_id, character_id, quest_template_id, detail_type, detail_id, status, created_at) " +
                "VALUES (@attempt_id, @act_id, @character_id, @quest_template_id, @detail_type, @detail_id, 0, UTC_TIMESTAMP())";
            AddKeyParameters(command, key);
            if (command.ExecuteNonQuery() == 1)
                return QuestRewardLedgerState.Pending;
            return Inspect(key);
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Could not reserve quest reward attempt {0}, act {1}", key.AttemptId, key.ActId);
            return QuestRewardLedgerState.Unavailable;
        }
    }

    private void Release(QuestRewardLedgerKey key)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText =
                "DELETE FROM quest_reward_ledger WHERE attempt_id=@attempt_id AND act_id=@act_id AND status=0";
            AddKeyParameters(command, key);
            command.ExecuteNonQuery();
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Could not release failed quest reward attempt {0}, act {1}; it remains pending",
                key.AttemptId, key.ActId);
        }
    }

    private static bool TryCreateKey(Quest quest, QuestAct questAct, out QuestRewardLedgerKey key)
    {
        if (quest?.Owner is not Character character || questAct?.Template is null ||
            quest.RewardAttemptId == Guid.Empty || questAct.Id == 0)
        {
            key = default;
            return false;
        }

        key = new QuestRewardLedgerKey(quest.RewardAttemptId, questAct.Id, character.Id,
            quest.TemplateId, questAct.Template.GetType().Name, questAct.DetailId);
        return true;
    }

    private static void AddKeyParameters(MySql.Data.MySqlClient.MySqlCommand command, QuestRewardLedgerKey key)
    {
        command.Parameters.AddWithValue("@attempt_id", key.AttemptId.ToByteArray());
        command.Parameters.AddWithValue("@act_id", key.ActId);
        command.Parameters.AddWithValue("@character_id", key.CharacterId);
        command.Parameters.AddWithValue("@quest_template_id", key.QuestTemplateId);
        command.Parameters.AddWithValue("@detail_type", key.DetailType);
        command.Parameters.AddWithValue("@detail_id", key.DetailId);
    }

    private static void LogBlocked(QuestRewardLedgerKey key, QuestRewardLedgerState state) => Logger.Warn(
        "Quest reward blocked for character {0}, quest {1}, attempt {2}, act {3}: ledger state {4}",
        key.CharacterId, key.QuestTemplateId, key.AttemptId, key.ActId, state);
}
