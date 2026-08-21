using System.Collections.Concurrent;
using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.ArchePass;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Core.Managers;

/// <summary>
/// AA10 character ArchePass ownership, progression and reward lifecycle. Mission rerolls remain
/// closed because retail r575 names content-config keys 277-280 but ships no values for them.
/// </summary>
public class ArchePassManager : Singleton<ArchePassManager>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly ConcurrentDictionary<uint, PassBook> _books = new();
    private readonly ConcurrentDictionary<uint, object> _characterLocks = new();

    public void SendInitialState(Character character)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            SendStateLocked(character, book);
        }
    }

    public void RejectMutation(Character character, string operation)
    {
        if (character is null)
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            RejectLocked(character, book, operation,
                "authoritative mission reset/change limits are absent from content_configs");
        }
    }

    public bool CanAddQuestPoints(Character character, int point)
    {
        if (character is null || point < 0)
            return false;
        if (point == 0)
            return true;
        if (!IsEnabled())
            return false;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            return book.PersistenceReady && TryGetActive(book, out var state) &&
                   IsProgressable(state);
        }
    }

    public bool TryAddQuestPoints(Character character, int point)
    {
        if (character is null || point < 0)
            return false;
        if (point == 0)
            return true;
        if (!IsEnabled())
            return false;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            if (!book.PersistenceReady || !TryGetActive(book, out var state) ||
                !IsProgressable(state))
            {
                RejectLocked(character, book, $"quest points +{point}",
                    "there is no valid persisted pass in progress");
                return false;
            }

            var template = ArchePassGameData.Instance.GetPass(state.Type);
            state.Point = ArchePassProgression.AddPoints(template, state.Point, point);
            SendStateLocked(character, book);
            return true;
        }
    }

    public void TryBuy(Character character, int type)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            var template = ArchePassGameData.Instance.GetPass(type);
            var existing = book.States.GetValueOrDefault(type);
            if (!book.PersistenceReady || template is null ||
                !template.IsAvailableAt(ServerCalendar.UtcNow) || HasOpenSlot(book) ||
                (existing is not null && existing.Status != ArchePassStatus.Dropped))
            {
                RejectLocked(character, book, $"buy type={type}", "pass is unavailable or the slot is full");
                return;
            }

            if (!character.TryPayCurrency(template.CurrencyId, template.CurrencyValue, false, ItemTaskType.StoreBuy))
            {
                RejectLocked(character, book, $"buy type={type}", "the configured currency could not be paid");
                return;
            }

            book.States[type] = new CharacterArchePassState
            {
                Type = type,
                Status = ArchePassStatus.Owned
            };
            SendStateLocked(character, book);
        }
    }

    public void TryStart(Character character, int type)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            var state = book.States.GetValueOrDefault(type);
            if (!book.PersistenceReady || state?.Status != ArchePassStatus.Owned ||
                book.States.Values.Any(value => value.Status == ArchePassStatus.Progress) ||
                !IsProgressable(state))
            {
                RejectLocked(character, book, $"start type={type}", "the owned pass cannot be started");
                return;
            }

            state.Status = ArchePassStatus.Progress;
            SendStateLocked(character, book);
        }
    }

    public void TryRemove(Character character, int type)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            var state = book.States.GetValueOrDefault(type);
            if (!book.PersistenceReady || state?.Status != ArchePassStatus.Progress)
            {
                RejectLocked(character, book, $"remove type={type}", "the pass is not in progress");
                return;
            }

            state.Status = ArchePassStatus.Dropped;
            SendStateLocked(character, book);
        }
    }

    public void TryUpgradePremium(Character character)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            if (!book.PersistenceReady || !TryGetActive(book, out var state) || state.Premium)
            {
                RejectLocked(character, book, "upgrade", "there is no non-premium pass in progress");
                return;
            }

            var template = ArchePassGameData.Instance.GetPass(state.Type);
            if (template is null || template.UpgradeItemId == 0 ||
                character.Inventory.GetItemsCount(SlotType.Inventory, template.UpgradeItemId) < 1 ||
                character.Inventory.Bag.ConsumeItem(
                    ItemTaskType.QuestComplete, template.UpgradeItemId, 1, null) != 1)
            {
                character.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
                RejectLocked(character, book, "upgrade", "the configured upgrade item is missing");
                return;
            }

            state.Premium = true;
            SendStateLocked(character, book);
        }
    }

    public void TryClaimReward(Character character, uint requestedTier, bool premium)
    {
        if (character is null || !IsEnabled() || requestedTier > int.MaxValue)
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            if (!book.PersistenceReady || !TryGetActive(book, out var state) || (premium && !state.Premium))
            {
                RejectLocked(character, book, $"reward tier={requestedTier} premium={premium}",
                    "there is no eligible pass in progress");
                return;
            }

            var template = ArchePassGameData.Instance.GetPass(state.Type);
            var nextTier = ArchePassProgression.GetNextClaimableTier(template, state, premium, true);
            if (nextTier == 0 || nextTier != (int)requestedTier)
            {
                RejectLocked(character, book, $"reward tier={requestedTier} premium={premium}",
                    "reward claims must follow the native sequential tier frontier");
                return;
            }

            var tier = template.Tiers.Single(value => value.Tier == nextTier);
            var reward = premium
                ? (tier.PremiumRewardItemId, tier.PremiumRewardItemCount, 0)
                : (tier.RewardItemId, tier.RewardItemCount, 0);
            var rewards = new[] { reward };
            var bag = character.Inventory.Bag;
            if (!bag.CanAcquireDefaultItems(rewards))
            {
                character.SendErrorMessage(ErrorMessageType.BagFull);
                RejectLocked(character, book, $"reward tier={requestedTier} premium={premium}",
                    "the bag cannot hold the configured reward");
                return;
            }

            var tasks = new List<ItemTask>();
            if (!bag.TryAcquireDefaultItemsIntoTaskBatch(rewards, tasks))
            {
                RejectLocked(character, book, $"reward tier={requestedTier} premium={premium}",
                    "the preflighted reward could not be acquired");
                return;
            }

            if (premium)
                state.LastPremiumRewardTier = nextTier;
            else
                state.LastRewardTier = nextTier;

            if (ArchePassProgression.CanCompletePremium(template, state))
                state.Status = ArchePassStatus.Completed;

            foreach (var task in tasks)
                character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.TodReward, task, []));
            SendStateLocked(character, book);
        }
    }

    public void TryCompleteNormal(Character character, int type)
    {
        if (character is null || !IsEnabled())
            return;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            var state = book.States.GetValueOrDefault(type);
            var template = ArchePassGameData.Instance.GetPass(type);
            if (!book.PersistenceReady || state?.Status != ArchePassStatus.Progress ||
                !ArchePassProgression.CanCompleteNormal(template, state))
            {
                RejectLocked(character, book, $"normal complete type={type}",
                    "the maximum tier or normal reward frontier is incomplete");
                return;
            }

            state.Status = ArchePassStatus.Completed;
            SendStateLocked(character, book);
        }
    }

    /// <summary>Persists pass mutations in the same character-save transaction as quest ledger completion.</summary>
    public void Save(Character character, MySqlConnection connection, MySqlTransaction transaction)
    {
        if (character is null || !_books.TryGetValue(character.Id, out var book) || !book.PersistenceReady)
            return;

        lock (GetLock(character))
        {
            foreach (var state in book.States.Values)
            {
                using var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText = """
                    INSERT INTO character_arche_passes
                        (character_id, arche_pass_id, point, status, premium,
                         last_reward_tier, last_premium_reward_tier, updated_at)
                    VALUES
                        (@character_id, @arche_pass_id, @point, @status, @premium,
                         @last_reward_tier, @last_premium_reward_tier, UTC_TIMESTAMP())
                    ON DUPLICATE KEY UPDATE
                        point = VALUES(point), status = VALUES(status), premium = VALUES(premium),
                        last_reward_tier = VALUES(last_reward_tier),
                        last_premium_reward_tier = VALUES(last_premium_reward_tier),
                        updated_at = VALUES(updated_at)
                    """;
                command.Parameters.AddWithValue("@character_id", character.Id);
                command.Parameters.AddWithValue("@arche_pass_id", state.Type);
                command.Parameters.AddWithValue("@point", state.Point);
                command.Parameters.AddWithValue("@status", (byte)state.Status);
                command.Parameters.AddWithValue("@premium", state.Premium);
                command.Parameters.AddWithValue("@last_reward_tier", state.LastRewardTier);
                command.Parameters.AddWithValue("@last_premium_reward_tier", state.LastPremiumRewardTier);
                command.ExecuteNonQuery();
            }
        }
    }

    private static bool IsEnabled() =>
        FeaturesManager.Fsets?.Check(Feature.arche_pass) == true;

    private object GetLock(Character character) =>
        _characterLocks.GetOrAdd(character.Id, _ => new object());

    private PassBook EnsureLoaded(Character character)
    {
        if (_books.TryGetValue(character.Id, out var cached))
            return cached;

        var book = new PassBook();
        try
        {
            using var connection = MySQL.CreateConnection();
            using var command = connection.CreateCommand();
            command.CommandText = """
                SELECT arche_pass_id, point, status, premium,
                       last_reward_tier, last_premium_reward_tier
                FROM character_arche_passes
                WHERE character_id = @character_id
                ORDER BY arche_pass_id
                """;
            command.Parameters.AddWithValue("@character_id", character.Id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var statusValue = reader.GetByte("status");
                if (!Enum.IsDefined(typeof(ArchePassStatus), statusValue) || statusValue == 0)
                    continue;
                var type = reader.GetInt32("arche_pass_id");
                book.States[type] = new CharacterArchePassState
                {
                    Type = type,
                    Point = Math.Max(0, reader.GetInt64("point")),
                    Status = (ArchePassStatus)statusValue,
                    Premium = reader.GetBoolean("premium"),
                    LastRewardTier = Math.Max(0, reader.GetInt32("last_reward_tier")),
                    LastPremiumRewardTier = Math.Max(0, reader.GetInt32("last_premium_reward_tier"))
                };
            }

            ReconcileExpiry(book);
            book.PersistenceReady = book.States.Values.Count(IsOpen) <= 1;
            if (!book.PersistenceReady)
                Logger.Error("ArchePass persistence invariant failed for character {0}: multiple open passes", character.Id);
        }
        catch (MySqlException exception)
        {
            Logger.Error(exception,
                "ArchePass persistence unavailable for {0}/{1}; mutations remain closed until migration is applied",
                character.Name, character.Id);
        }

        _books[character.Id] = book;
        return book;
    }

    private static void ReconcileExpiry(PassBook book)
    {
        var now = ServerCalendar.UtcNow;
        foreach (var state in book.States.Values.Where(IsOpen))
        {
            var endAt = ArchePassGameData.Instance.GetPass(state.Type)?.EndAtUtc;
            if (endAt is not null && now >= endAt.Value)
                state.Status = ArchePassStatus.Expired;
        }
    }

    private static bool IsOpen(CharacterArchePassState state) =>
        state.Status is ArchePassStatus.Owned or ArchePassStatus.Progress;

    private static bool HasOpenSlot(PassBook book) => book.States.Values.Any(IsOpen);

    private static bool TryGetActive(PassBook book, out CharacterArchePassState state)
    {
        state = book.States.Values.SingleOrDefault(value => value.Status == ArchePassStatus.Progress);
        return state is not null;
    }

    private static bool IsProgressable(CharacterArchePassState state)
    {
        var template = ArchePassGameData.Instance.GetPass(state.Type);
        return template is not null && template.IsAvailableAt(ServerCalendar.UtcNow);
    }

    private static void SendStateLocked(Character character, PassBook book)
    {
        var pages = book.States.Values
            .OrderBy(state => state.Type)
            .Select(ToWireState)
            .Chunk(10)
            .ToArray();
        if (pages.Length == 0)
            character.SendPacket(new SCArchePassesPacket([], true));
        else
            for (var index = 0; index < pages.Length; index++)
                character.SendPacket(new SCArchePassesPacket(pages[index], index == pages.Length - 1));

        // These are mission-completion bitsets, not completed-pass history. Their source remains
        // closed with the absent reset/count configuration, so an empty native list is intentional.
        character.SendPacket(new SCCompletedArchePassesPacket([]));
        character.SendPacket(new SCArchePassMissionCountPacket(0));
        character.SendPacket(new SCArchePassChangeMissionPacket(0));
    }

    private static ArchePassWireState ToWireState(CharacterArchePassState state) => new(
        state.Type,
        state.Point,
        (byte)state.Status,
        state.Premium,
        state.LastRewardTier,
        state.LastPremiumRewardTier);

    private static void RejectLocked(Character character, PassBook book, string operation, string reason)
    {
        Logger.Warn("ArchePass {0} rejected for {1}/{2}: {3}",
            operation, character.Name, character.AccountId, reason);
        SendStateLocked(character, book);
    }

    private sealed class PassBook
    {
        public bool PersistenceReady { get; set; }
        public Dictionary<int, CharacterArchePassState> States { get; } = [];
    }
}
