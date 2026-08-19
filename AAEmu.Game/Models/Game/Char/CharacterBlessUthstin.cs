using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;

using MySql.Data.MySqlClient;

using NLog;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// Server-authoritative AA10 Migration Scaling state. Page and stat indexes are zero-based on the
/// wire; the Lua binding converts its one-based UI values before emitting the C2G packets.
/// </summary>
public sealed class CharacterBlessUthstin(Character owner)
{
    public const int MaximumPageCount = 3;

    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
    private readonly object _sync = new();
    private readonly List<BlessUthstinPage> _pages = [new()];
    private BlessUthstinRoll _pendingRoll;
    private DateTime _resetDateUtc = DateTime.UtcNow.Date;

    private Character Owner { get; } = owner;

    public int ActivePageIndex { get; private set; }
    public int ExtendedMaximumStats { get; private set; }
    public int ApplyExtendCount { get; private set; }

    public int PageCount
    {
        get
        {
            lock (_sync)
                return _pages.Count;
        }
    }

    public static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.bless_uthstin);

    public int GetAppliedStat(BlessUthstinStat stat)
    {
        lock (_sync)
            return _pages[ActivePageIndex].Stats[(int)stat];
    }

    public IReadOnlyList<BlessUthstinPage> GetPagesSnapshot()
    {
        lock (_sync)
            return _pages.Select(page => page.Clone()).ToArray();
    }

    public void Load(MySqlConnection connection)
    {
        lock (_sync)
        {
            _pages.Clear();
            _pages.Add(new BlessUthstinPage());
            ActivePageIndex = 0;
            ExtendedMaximumStats = 0;
            ApplyExtendCount = 0;
            _pendingRoll = null;
            _resetDateUtc = DateTime.UtcNow.Date;

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT active_page, page_count, extended_max_stats, extend_count, reset_date " +
                    "FROM character_bless_uthstin WHERE owner = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using var reader = command.ExecuteReader();
                if (reader.Read())
                {
                    var pageCount = Math.Clamp(reader.GetInt32("page_count"), 1, MaximumPageCount);
                    _pages.Clear();
                    for (var index = 0; index < pageCount; index++)
                        _pages.Add(new BlessUthstinPage());

                    ActivePageIndex = Math.Clamp(reader.GetInt32("active_page"), 0, pageCount - 1);
                    ExtendedMaximumStats = Math.Max(0, reader.GetInt32("extended_max_stats"));
                    ApplyExtendCount = Math.Max(0, reader.GetInt32("extend_count"));
                    _resetDateUtc = reader.GetDateTime("reset_date").Date;
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT page_index, stat_str, stat_dex, stat_sta, stat_int, stat_spi, " +
                    "normal_apply_count, special_apply_count FROM character_bless_uthstin_pages " +
                    "WHERE owner = @owner ORDER BY page_index";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using var reader = command.ExecuteReader();
                while (reader.Read())
                {
                    var pageIndex = reader.GetInt32("page_index");
                    if (pageIndex < 0 || pageIndex >= _pages.Count)
                        continue;

                    var page = _pages[pageIndex];
                    page.Stats[0] = reader.GetInt32("stat_str");
                    page.Stats[1] = reader.GetInt32("stat_dex");
                    page.Stats[2] = reader.GetInt32("stat_sta");
                    page.Stats[3] = reader.GetInt32("stat_int");
                    page.Stats[4] = reader.GetInt32("stat_spi");
                    page.NormalApplyCount = Math.Max(0, reader.GetInt32("normal_apply_count"));
                    page.SpecialApplyCount = Math.Max(0, reader.GetInt32("special_apply_count"));
                }
            }

            // Both counters are presented by the exact Lua under "Daily Usage Count".
            if (_resetDateUtc < DateTime.UtcNow.Date)
            {
                foreach (var page in _pages)
                {
                    page.NormalApplyCount = 0;
                    page.SpecialApplyCount = 0;
                }
                _resetDateUtc = DateTime.UtcNow.Date;
            }
        }
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        lock (_sync)
            SaveSnapshot(connection, transaction, _pages, ActivePageIndex, ExtendedMaximumStats,
                ApplyExtendCount, _resetDateUtc);
    }

    public bool TryConsumeApplyStats(ulong itemInstanceId, int pageIndex, Random random = null)
    {
        lock (_sync)
        {
            if (!IsFeatureEnabled(FeaturesManager.Fsets) || !IsValidPage(pageIndex))
                return SendConsumeResult(false, null);

            EnsureDailyReset();

            var selectedItem = Owner.Inventory.Bag.GetItemByItemId(itemInstanceId);
            var definition = selectedItem is null
                ? null
                : BlessUthstinGameData.Instance.GetItem(selectedItem.TemplateId);
            if (definition is null)
                return SendConsumeResult(false, null);

            var page = _pages[pageIndex];
            if (definition.FunctionId == 1 &&
                page.NormalApplyCount >= BlessUthstinGameData.Instance.NormalDailyApplyLimit)
                return SendConsumeResult(false, null);

            var applyCount = definition.FunctionId == 1
                ? page.NormalApplyCount
                : page.SpecialApplyCount;
            var requiredItemCount = GetRequiredItemCount(applyCount);

            var defaultStats = Owner.GetBlessUthstinDefaultStats();
            var maximumStats = checked(BlessUthstinGameData.Instance.BaseMaximumStats + ExtendedMaximumStats);
            var roll = BlessUthstinCalculator.Resolve(
                definition,
                page.Stats,
                defaultStats,
                maximumStats,
                random ?? Random.Shared);
            if (roll is null)
                return SendConsumeResult(false, null);

            roll = roll with { PageIndex = pageIndex };
            if (!Owner.Inventory.Bag.TryConsumeExactTemplates(
                    ItemTaskType.BlessUthstinChangeStats,
                    [(definition.ItemId, requiredItemCount)]))
                return SendConsumeResult(false, null);

            _pendingRoll = roll;
            return SendConsumeResult(true, roll);
        }
    }

    public bool TryApplyStats(
        bool apply,
        int itemTemplateId,
        uint increaseStat,
        uint decreaseStat,
        uint increasePoints,
        uint decreasePoints,
        int pageIndex)
    {
        lock (_sync)
        {
            var pending = _pendingRoll;
            _pendingRoll = null;
            if (!IsFeatureEnabled(FeaturesManager.Fsets) || pending is null ||
                !MatchesPending(pending, itemTemplateId, increaseStat, decreaseStat,
                    increasePoints, decreasePoints, pageIndex))
                return SendApplyResult(false, IsValidPage(pageIndex) ? pageIndex : ActivePageIndex, false);

            // Native cancel deliberately keeps the already consumed item and discards the preview.
            if (!apply)
                return SendApplyResult(false, pageIndex, false);

            var nextPages = _pages.Select(page => page.Clone()).ToList();
            var nextPage = nextPages[pageIndex];
            nextPage.Stats[(int)pending.IncreaseStat] = checked(
                nextPage.Stats[(int)pending.IncreaseStat] + pending.IncreasePoints);
            nextPage.Stats[(int)pending.DecreaseStat] = checked(
                nextPage.Stats[(int)pending.DecreaseStat] - pending.DecreasePoints);
            if (pending.FunctionId == 1)
                nextPage.NormalApplyCount++;
            else
                nextPage.SpecialApplyCount++;

            if (!TryPersistSnapshot(nextPages, ActivePageIndex, ExtendedMaximumStats, ApplyExtendCount))
                return SendApplyResult(false, pageIndex, false);

            _pages.Clear();
            _pages.AddRange(nextPages);
            return SendApplyResult(true, pageIndex, false);
        }
    }

    public void SendLoginState()
    {
        if (!IsFeatureEnabled(FeaturesManager.Fsets))
            return;

        lock (_sync)
        {
            for (var pageIndex = 0; pageIndex < _pages.Count; pageIndex++)
                SendApplyResult(true, pageIndex, true);
            Owner.SendPacket(new SCBlessUthstinSelectPagePacket(Owner.ObjId, true, ActivePageIndex));
        }
    }

    /// <summary>
    /// Reset/extension/page-management packets are wire-closed but are not part of this first
    /// stat-replacement reconstruction. Reply explicitly so the retail dialog never waits forever.
    /// </summary>
    public void RejectInitStats(int pageIndex) =>
        Owner.SendPacket(new SCBlessUthstinInitStatsPacket(Owner.ObjId, false, pageIndex));

    public void RejectExtendMaximumStats() =>
        Owner.SendPacket(new SCBlessUthstinExtendMaxStatsPacket(
            Owner.ObjId, false, checked((uint)ExtendedMaximumStats), checked((uint)ApplyExtendCount)));

    public void RejectExpandPage() =>
        Owner.SendPacket(new SCBlessUthstinExpandPagePacket(Owner.ObjId, false, PageCount));

    public void RejectCopyPage(int destinationPageIndex)
    {
        lock (_sync)
        {
            var page = IsValidPage(destinationPageIndex)
                ? _pages[destinationPageIndex]
                : new BlessUthstinPage();
            Owner.SendPacket(new SCBlessUthstinCopyPagePacket(
                Owner.ObjId,
                false,
                destinationPageIndex,
                page.Stats,
                page.NormalApplyCount,
                page.SpecialApplyCount));
        }
    }

    private bool SendConsumeResult(bool result, BlessUthstinRoll roll)
    {
        Owner.SendPacket(new SCBlessUthstinConsumeApplyStatsPacket(
            Owner.ObjId,
            result,
            roll is null ? 0 : checked((int)roll.ItemTemplateId),
            roll is null ? 0u : (uint)roll.IncreaseStat,
            roll is null ? 0u : (uint)roll.DecreaseStat,
            roll is null ? 0u : checked((uint)roll.IncreasePoints),
            roll is null ? 0u : checked((uint)roll.DecreasePoints)));
        return result;
    }

    private bool SendApplyResult(bool result, int pageIndex, bool login)
    {
        var page = _pages[Math.Clamp(pageIndex, 0, _pages.Count - 1)];
        Owner.SendPacket(new SCBlessUthstinApplyStatsPacket(
            Owner.ObjId,
            result,
            page.Stats,
            pageIndex,
            checked((uint)page.NormalApplyCount),
            checked((uint)page.SpecialApplyCount),
            login));
        return result;
    }

    private bool TryPersistSnapshot(
        IReadOnlyList<BlessUthstinPage> pages,
        int activePage,
        int extendedMaximumStats,
        int applyExtendCount)
    {
        try
        {
            using var connection = MySQL.CreateConnection();
            using var transaction = connection.BeginTransaction();
            SaveSnapshot(connection, transaction, pages, activePage, extendedMaximumStats,
                applyExtendCount, _resetDateUtc);
            transaction.Commit();
            return true;
        }
        catch (Exception exception)
        {
            Logger.Error(exception, "Failed to persist Bless Uthstin state for {0}", Owner.Name);
            return false;
        }
    }

    private void SaveSnapshot(
        MySqlConnection connection,
        MySqlTransaction transaction,
        IReadOnlyList<BlessUthstinPage> pages,
        int activePage,
        int extendedMaximumStats,
        int applyExtendCount,
        DateTime resetDateUtc)
    {
        using (var command = connection.CreateCommand())
        {
            command.Transaction = transaction;
            command.CommandText =
                "INSERT INTO character_bless_uthstin " +
                "(owner, active_page, page_count, extended_max_stats, extend_count, reset_date) " +
                "VALUES (@owner, @activePage, @pageCount, @extendedMaximumStats, @extendCount, @resetDate) " +
                "ON DUPLICATE KEY UPDATE active_page = VALUES(active_page), page_count = VALUES(page_count), " +
                "extended_max_stats = VALUES(extended_max_stats), extend_count = VALUES(extend_count), " +
                "reset_date = VALUES(reset_date)";
            command.Parameters.AddWithValue("@owner", Owner.Id);
            command.Parameters.AddWithValue("@activePage", activePage);
            command.Parameters.AddWithValue("@pageCount", pages.Count);
            command.Parameters.AddWithValue("@extendedMaximumStats", extendedMaximumStats);
            command.Parameters.AddWithValue("@extendCount", applyExtendCount);
            command.Parameters.AddWithValue("@resetDate", resetDateUtc.Date);
            command.ExecuteNonQuery();
        }

        for (var pageIndex = 0; pageIndex < pages.Count; pageIndex++)
        {
            var page = pages[pageIndex];
            using var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText =
                "INSERT INTO character_bless_uthstin_pages " +
                "(owner, page_index, stat_str, stat_dex, stat_sta, stat_int, stat_spi, " +
                "normal_apply_count, special_apply_count) VALUES " +
                "(@owner, @pageIndex, @str, @dex, @sta, @int, @spi, @normalCount, @specialCount) " +
                "ON DUPLICATE KEY UPDATE stat_str = VALUES(stat_str), stat_dex = VALUES(stat_dex), " +
                "stat_sta = VALUES(stat_sta), stat_int = VALUES(stat_int), stat_spi = VALUES(stat_spi), " +
                "normal_apply_count = VALUES(normal_apply_count), " +
                "special_apply_count = VALUES(special_apply_count)";
            command.Parameters.AddWithValue("@owner", Owner.Id);
            command.Parameters.AddWithValue("@pageIndex", pageIndex);
            command.Parameters.AddWithValue("@str", page.Stats[0]);
            command.Parameters.AddWithValue("@dex", page.Stats[1]);
            command.Parameters.AddWithValue("@sta", page.Stats[2]);
            command.Parameters.AddWithValue("@int", page.Stats[3]);
            command.Parameters.AddWithValue("@spi", page.Stats[4]);
            command.Parameters.AddWithValue("@normalCount", page.NormalApplyCount);
            command.Parameters.AddWithValue("@specialCount", page.SpecialApplyCount);
            command.ExecuteNonQuery();
        }
    }

    internal static int GetRequiredItemCount(int applyCount) =>
        applyCount <= 0 ? 1 : checked(applyCount * applyCount + 1);

    private bool IsValidPage(int pageIndex) => pageIndex >= 0 && pageIndex < _pages.Count;

    private void EnsureDailyReset()
    {
        var todayUtc = DateTime.UtcNow.Date;
        if (_resetDateUtc >= todayUtc)
            return;

        foreach (var page in _pages)
        {
            page.NormalApplyCount = 0;
            page.SpecialApplyCount = 0;
        }
        _resetDateUtc = todayUtc;
    }

    internal static bool MatchesPending(
        BlessUthstinRoll pending,
        int itemTemplateId,
        uint increaseStat,
        uint decreaseStat,
        uint increasePoints,
        uint decreasePoints,
        int pageIndex) =>
        itemTemplateId >= 0 && pending.ItemTemplateId == (uint)itemTemplateId &&
        (uint)pending.IncreaseStat == increaseStat &&
        (uint)pending.DecreaseStat == decreaseStat &&
        pending.IncreasePoints >= 0 && (uint)pending.IncreasePoints == increasePoints &&
        pending.DecreasePoints >= 0 && (uint)pending.DecreasePoints == decreasePoints &&
        pending.PageIndex == pageIndex;
}
