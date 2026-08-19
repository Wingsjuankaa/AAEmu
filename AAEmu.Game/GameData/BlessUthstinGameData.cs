using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData;

/// <summary>
/// AA10 r575 Migration Scaling catalogue and limits. All values are loaded from the exact client
/// SQLite instead of being duplicated in server configuration.
/// </summary>
[GameData]
public sealed class BlessUthstinGameData : Singleton<BlessUthstinGameData>, IGameDataLoader
{
    private readonly Dictionary<uint, ItemBlessUthstinDefinition> _items = [];

    public int BaseMaximumStats { get; private set; }
    public int MaximumStatsLimit { get; private set; }
    public int MaximumStatsPerExtension { get; private set; }
    public int NormalDailyApplyLimit { get; private set; }
    public uint InitItemType { get; private set; }
    public uint ExtendMaximumItemType { get; private set; }
    public int InitItemCount { get; private set; }
    public int SelectPageMoneyCost { get; private set; }
    public int CopyPageMoneyCost { get; private set; }
    public uint ExpandPageItemType { get; private set; }
    public int SecondPageItemCount { get; private set; }
    public int ThirdPageItemCount { get; private set; }

    public ItemBlessUthstinDefinition GetItem(uint itemId) =>
        itemId == 0 ? null : _items.GetValueOrDefault(itemId);

    public void Load(SqliteConnection connection)
    {
        _items.Clear();

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT item_id, drop_count, drop_weight_str, drop_weight_dex, drop_weight_sta, " +
                "drop_weight_int, drop_weight_spi, function_id, rise_count, rise_weight_str, " +
                "rise_weight_dex, rise_weight_sta, rise_weight_int, rise_weight_spi " +
                "FROM item_bless_uthstins ORDER BY item_id";
            command.Prepare();
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var definition = new ItemBlessUthstinDefinition
                {
                    ItemId = reader.GetUInt32("item_id"),
                    DropCount = reader.GetInt32("drop_count", 0),
                    DropWeights =
                    [
                        reader.GetInt32("drop_weight_str", 0),
                        reader.GetInt32("drop_weight_dex", 0),
                        reader.GetInt32("drop_weight_sta", 0),
                        reader.GetInt32("drop_weight_int", 0),
                        reader.GetInt32("drop_weight_spi", 0)
                    ],
                    FunctionId = reader.GetInt32("function_id", 0),
                    RiseCount = reader.GetInt32("rise_count", 0),
                    RiseWeights =
                    [
                        reader.GetInt32("rise_weight_str", 0),
                        reader.GetInt32("rise_weight_dex", 0),
                        reader.GetInt32("rise_weight_sta", 0),
                        reader.GetInt32("rise_weight_int", 0),
                        reader.GetInt32("rise_weight_spi", 0)
                    ]
                };

                if (!_items.TryAdd(definition.ItemId, definition))
                    throw new InvalidDataException($"Duplicate item_bless_uthstins item_id {definition.ItemId}.");
            }
        }

        var configs = LoadConfigs(connection);
        BaseMaximumStats = RequireConfig(configs, "bless_uthstin_base_stats");
        MaximumStatsLimit = RequireConfig(configs, "bless_uthstin_max_stats_limit");
        MaximumStatsPerExtension = RequireConfig(configs, "bless_uthstin_max_stats_extend_per_point");
        NormalDailyApplyLimit = RequireConfig(configs, "bless_uthstin_apply_limit_count");
        InitItemType = checked((uint)RequireConfig(configs, "bless_uthstin_Init_ItemType"));
        ExtendMaximumItemType = checked((uint)RequireConfig(configs, "bless_uthstin_max_stats_extend_ItemType"));
        InitItemCount = RequireConfig(configs, "bless_uthstin_Init_Item_Num");
        SelectPageMoneyCost = RequireConfig(configs, "bless_uthstin_select_cost");
        CopyPageMoneyCost = RequireConfig(configs, "bless_uthstin_copy_cost");
        ExpandPageItemType = checked((uint)RequireConfig(configs, "bless_uthstin_expand_page_item_type"));
        SecondPageItemCount = RequireConfig(configs, "bless_uthstin_expand_item_count_for_page_2");
        ThirdPageItemCount = RequireConfig(configs, "bless_uthstin_expand_item_count_for_page_3");
    }

    public void PostLoad()
    {
        if (_items.Count == 0 || BaseMaximumStats <= 0 ||
            MaximumStatsLimit < BaseMaximumStats || MaximumStatsPerExtension <= 0 ||
            NormalDailyApplyLimit <= 0 || InitItemType == 0 || ExtendMaximumItemType == 0 ||
            InitItemCount <= 0 || SelectPageMoneyCost < 0 || CopyPageMoneyCost < 0 ||
            ExpandPageItemType == 0 || SecondPageItemCount <= 0 || ThirdPageItemCount <= 0)
            throw new InvalidDataException("Invalid AA10 Bless Uthstin content configuration.");

        foreach (var definition in _items.Values)
        {
            var template = ItemManager.Instance.GetTemplate(definition.ItemId);
            if (template is null || template.ImplId != ItemImplEnum.BlessUthstin ||
                definition.FunctionId is not (1 or 2) ||
                definition.RiseCount <= 0 || definition.DropCount <= 0 ||
                definition.RiseWeights.Any(weight => weight < 0) ||
                definition.DropWeights.Any(weight => weight < 0) ||
                definition.RiseWeights.All(weight => weight == 0) ||
                definition.DropWeights.All(weight => weight == 0))
                throw new InvalidDataException(
                    $"Invalid item_bless_uthstins definition for item {definition.ItemId}.");
        }
    }

    private static Dictionary<string, int> LoadConfigs(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT e.name, c.value FROM content_configs c " +
            "JOIN enum_content_configs e ON e.id = c.id WHERE c.kind_id = 35";
        command.Prepare();
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        var result = new Dictionary<string, int>(StringComparer.Ordinal);
        while (reader.Read())
            result.Add(reader.GetString("name"), reader.GetInt32("value", 0));
        return result;
    }

    private static int RequireConfig(IReadOnlyDictionary<string, int> configs, string name)
    {
        if (!configs.TryGetValue(name, out var value))
            throw new InvalidDataException($"Missing required content config '{name}'.");
        return value;
    }
}
