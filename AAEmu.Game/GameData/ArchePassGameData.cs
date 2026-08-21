using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.ArchePass;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.GameData;

/// <summary>Relational loader for the AA10 ArchePass category, pass and tier catalog.</summary>
[GameData]
public class ArchePassGameData : Singleton<ArchePassGameData>, IGameDataLoader
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private Dictionary<int, ArchePassTemplate> _passes = [];

    public void Load(SqliteConnection connection)
    {
        var categories = new Dictionary<uint, bool>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT id, enable FROM arche_pass_categories";
            command.Prepare();
            using var sqliteReader = command.ExecuteReader();
            using var reader = new SQLiteWrapperReader(sqliteReader);
            while (reader.Read())
                categories[reader.GetUInt32("id")] = reader.GetBoolean("enable");
        }

        _passes = [];
        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                SELECT id, arche_pass_category_id, ed_year, ed_month, ed_day, ed_hour, ed_min,
                       currency_id, currency_value, upgrade_item_id, max_tier
                FROM arche_passes
                ORDER BY id
                """;
            command.Prepare();
            using var sqliteReader = command.ExecuteReader();
            using var reader = new SQLiteWrapperReader(sqliteReader);
            while (reader.Read())
            {
                var categoryId = reader.GetUInt32("arche_pass_category_id");
                _passes[reader.GetInt32("id")] = new ArchePassTemplate
                {
                    Id = reader.GetInt32("id"),
                    CategoryId = categoryId,
                    CategoryEnabled = categories.GetValueOrDefault(categoryId),
                    EndAtUtc = ParseEndAtUtc(
                        reader.GetInt32("ed_year"), reader.GetInt32("ed_month"),
                        reader.GetInt32("ed_day"), reader.GetInt32("ed_hour"),
                        reader.GetInt32("ed_min")),
                    CurrencyId = reader.GetUInt32("currency_id"),
                    CurrencyValue = reader.GetInt64("currency_value"),
                    UpgradeItemId = reader.GetUInt32("upgrade_item_id"),
                    MaxTier = reader.GetInt32("max_tier")
                };
            }
        }

        var tiers = new Dictionary<int, List<ArchePassTierTemplate>>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                SELECT arche_pass_id, tier, point, reward_item_id, reward_item_count,
                       premium_reward_item_id, premium_reward_item_count
                FROM arche_pass_tiers
                ORDER BY arche_pass_id, tier
                """;
            command.Prepare();
            using var sqliteReader = command.ExecuteReader();
            using var reader = new SQLiteWrapperReader(sqliteReader);
            while (reader.Read())
            {
                var passId = reader.GetInt32("arche_pass_id");
                if (!tiers.TryGetValue(passId, out var values))
                    tiers[passId] = values = [];
                values.Add(new ArchePassTierTemplate(
                    reader.GetInt32("tier"),
                    reader.GetInt64("point"),
                    reader.GetUInt32("reward_item_id", 0),
                    reader.GetInt32("reward_item_count"),
                    reader.GetUInt32("premium_reward_item_id", 0),
                    reader.GetInt32("premium_reward_item_count")));
            }
        }

        foreach (var (passId, template) in _passes)
            template.Tiers = tiers.GetValueOrDefault(passId) ?? [];

        Logger.Info(
            "Loaded {0} ArchePasses and {1} tiers ({2} currently purchasable)",
            _passes.Count, tiers.Values.Sum(values => values.Count),
            _passes.Values.Count(pass => pass.IsAvailableAt(DateTime.UtcNow)));
    }

    public void PostLoad()
    {
    }

    public ArchePassTemplate GetPass(int type) => _passes.GetValueOrDefault(type);

    public IReadOnlyCollection<ArchePassTemplate> Passes => _passes.Values;

    public static DateTime? ParseEndAtUtc(int year, int month, int day, int hour, int minute)
    {
        if (year == 0 && month == 0 && day == 0)
            return null;
        if (year is > 0 and < 100)
            year += 2000;
        try
        {
            return new DateTime(year, month, day, hour, minute, 0, DateTimeKind.Utc);
        }
        catch (ArgumentOutOfRangeException)
        {
            return DateTime.UnixEpoch;
        }
    }
}
