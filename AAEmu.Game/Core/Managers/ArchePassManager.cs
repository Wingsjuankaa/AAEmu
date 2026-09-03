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

    public bool HasActivePremiumPass(Character character)
    {
        if (character is null || !IsEnabled())
            return false;

        lock (GetLock(character))
        {
            var book = EnsureLoaded(character);
            ReconcileExpiry(book);
            if (!book.PersistenceReady || !TryGetActive(book, out var state))
                return false;

            return ArchePassMissionEligibility.HasPremiumAccess(book.PersistenceReady, state,
                ArchePassGameData.Instance.GetPass(state.Type), ServerCalendar.UtcNow);
        }
    }

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
        => TryAddPoints(character, point, out _);

    public bool TryAddPoints(Character character, int point, out ArchePassPointChange change)
    {
        change = null;
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
            var previousPoint = state.Point;
            state.Point = ArchePassProgression.AddPoints(template, state.Point, point);
            change = new ArchePassPointChange(state.Type, previousPoint, state.Point,
                ArchePassProgression.GetCurrentTier(template, state.Point));
            // r575 reason 1 emits ARCHE_PASS_UPDATE_POINT / ARCHE_PASS_UPDATE_TIER.
            // Initial-state pages do not notify the already-open Lua panel.
            character.SendPacket(new SCUpdateArchePassPacket(ToWireState(state),
                ArchePassUpdateReason.UpdatePoint, change.AppliedPoints, false));
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
            if (!book.PersistenceReady)
            {
                RejectLocked(character, book, $"buy type={type}", "persisted pass invariants are invalid");
                return;
            }

            if (template is null)
            {
                RejectLocked(character, book, $"buy type={type}", "the pass does not exist in the AA10 catalog");
                return;
            }

            if (!template.CategoryEnabled || !template.HasCompleteTierCatalog)
            {
                RejectLocked(character, book, $"buy type={type}",
                    "the category is disabled or the tier catalog is incomplete");
                return;
            }

            if (template.EndAtUtc is not null && ServerCalendar.UtcNow >= template.EndAtUtc.Value)
            {
                RejectLocked(character, book, $"buy type={type}",
                    $"the pass expired at {template.EndAtUtc.Value:O}");
                return;
            }

            if (IsRegistrationFull(book))
            {
                RejectLocked(character, book, $"buy type={type}",
                    $"the native capacity of {ArchePassRegistrationPolicy.Capacity} registered passes is full");
                return;
            }

            if (existing is not null && existing.Status != ArchePassStatus.Dropped)
            {
                RejectLocked(character, book, $"buy type={type}",
                    $"the pass already has status {existing.Status}");
                return;
            }

            if (!character.TryPayCurrency(template.CurrencyId, template.CurrencyValue, false, ItemTaskType.StoreBuy))
            {
                RejectLocked(character, book, $"buy type={type}", "the configured currency could not be paid");
                return;
            }

            var state = new CharacterArchePassState
            {
                Type = type,
                Status = ArchePassStatus.Owned
            };
            book.States[type] = state;

            // Retail r575 handles a successful CSArchePassBuy through reason 6. This inserts the
            // purchased state in the client's pass book and emits ARCHE_PASS_BUY, which makes the
            // newly registered pass visible/selected without requiring a relog.
            character.SendPacket(new SCUpdateArchePassPacket(
                ToWireState(state), ArchePassUpdateReason.Buy, 0, false));
            Logger.Info(
                "ArchePass buy committed type={0}, status={1}, registered={2}/{3} for {4}/{5}",
                type, state.Status, book.States.Values.Count(IsRegistered),
                ArchePassRegistrationPolicy.Capacity, character.Name, character.AccountId);
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
                !IsProgressable(state) ||
                !ArchePassRegistrationPolicy.TryActivate(
                    book.States, type, out var pausedState, out var startedState))
            {
                RejectLocked(character, book, $"start type={type}", "the owned pass cannot be started");
                return;
            }

            // The registry dialog explicitly promises that starting a new pass pauses the current
            // one. Update the old client record first so GetMyArchePassInfo has exactly one
            // Progress record when ARCHE_PASS_STARTED refreshes the main panel.
            if (pausedState is not null)
                character.SendPacket(new SCUpdateArchePassPacket(
                    ToWireState(pausedState), ArchePassUpdateReason.Owned, 0, false));

            // The r575 main ArchePass panel refreshes from ARCHE_PASS_STARTED. A full state page
            // is only a load/resync path and does not emit that Lua event.
            character.SendPacket(new SCUpdateArchePassPacket(
                ToWireState(startedState), ArchePassUpdateReason.Started, 0, false));
            Logger.Info(
                "ArchePass start committed type={0}, status={1}, pausedType={2} for {3}/{4}",
                type, startedState.Status, pausedState?.Type, character.Name, character.AccountId);
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
            // r575 reason 7 emits ARCHE_PASS_UPGRADE_PREMIUM after replacing the state.
            // A load page does not refresh an already-open premium/reward panel.
            character.SendPacket(new SCUpdateArchePassPacket(ToWireState(state),
                ArchePassUpdateReason.UpgradePremium, 0, false));
            Logger.Info("ArchePass premium upgraded: character={0} account={1} type={2} ticket={3} point={4} lastRewardTier={5} lastPremiumRewardTier={6}",
                character.Name, character.AccountId, state.Type, template.UpgradeItemId, state.Point,
                state.LastRewardTier, state.LastPremiumRewardTier);
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
            // r575 reason 2 updates both claim frontiers before emitting
            // ARCHE_PASS_UPDATE_REWARD_ITEM; initial-state pages do not refresh the reward UI.
            character.SendPacket(new SCUpdateArchePassPacket(ToWireState(state),
                ArchePassUpdateReason.UpdateRewardItem, 0, false));
            Logger.Info("ArchePass reward claimed: character={0} account={1} type={2} tier={3} premium={4} point={5} lastRewardTier={6} lastPremiumRewardTier={7}",
                character.Name, character.AccountId, state.Type, nextTier, premium, state.Point,
                state.LastRewardTier, state.LastPremiumRewardTier);
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
            book.PersistenceReady = ArchePassRegistrationPolicy.HasValidPersistenceState(
                book.States.Values.Select(state => state.Status));
            if (!book.PersistenceReady)
                Logger.Error(
                    "ArchePass persistence invariant failed for character {0}: registered={1}, active={2}, capacity={3}",
                    character.Id,
                    book.States.Values.Count(IsRegistered),
                    book.States.Values.Count(state => state.Status == ArchePassStatus.Progress),
                    ArchePassRegistrationPolicy.Capacity);
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
        foreach (var state in book.States.Values.Where(IsRegistered))
        {
            var endAt = ArchePassGameData.Instance.GetPass(state.Type)?.EndAtUtc;
            if (endAt is not null && now >= endAt.Value)
                state.Status = ArchePassStatus.Expired;
        }
    }

    private static bool IsRegistered(CharacterArchePassState state) =>
        ArchePassRegistrationPolicy.IsRegistered(state.Status);

    private static bool IsRegistrationFull(PassBook book) =>
        ArchePassRegistrationPolicy.IsFull(book.States.Values.Select(state => state.Status));

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
