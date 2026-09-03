using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData;

/// <summary>Exact AA10 r575 catalogue and content configuration for Item Lock.</summary>
[GameData]
public sealed class ItemSecurityGameData : Singleton<ItemSecurityGameData>, IGameDataLoader
{
    public const uint UnlockDelayConfigId = 43;
    public const uint MoneyConfigId = 214;
    public const uint EquipmentUiConfigId = 215;
    public const uint LockSecondPasswordConfigId = 222;
    public const uint UnlockSecondPasswordConfigId = 223;

    private HashSet<int> _secureCategoryIds = [];
    private HashSet<uint> _exceptionItemIds = [];

    public int SecureCategoryCount => _secureCategoryIds.Count;
    public int ExceptionItemCount => _exceptionItemIds.Count;
    public TimeSpan UnlockDelay { get; private set; }
    public long MoneyCost { get; private set; }
    public bool UseEquipmentUi { get; private set; }
    public bool UseSecondPasswordWhenLocking { get; private set; }
    public bool UseSecondPasswordWhenUnlocking { get; private set; }

    public bool IsEligible(ItemTemplate template) =>
        template is not null &&
        _secureCategoryIds.Contains(template.CategoryId) &&
        !_exceptionItemIds.Contains(template.Id);

    public void Load(SqliteConnection connection)
    {
        ArgumentNullException.ThrowIfNull(connection);

        var secureCategories = new HashSet<int>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT id, secure FROM item_categories";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                if (reader.GetBoolean("secure"))
                    secureCategories.Add(reader.GetInt32("id"));
        }

        var exceptions = new HashSet<uint>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT item_id FROM item_secure_exceptions";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                exceptions.Add(reader.GetUInt32("item_id"));
        }

        var configs = new Dictionary<uint, long>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT id, value FROM content_configs WHERE id IN (43, 214, 215, 222, 223)";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                configs[reader.GetUInt32("id")] = reader.GetInt64("value");
        }

        var requiredConfigIds = new[]
        {
            UnlockDelayConfigId,
            MoneyConfigId,
            EquipmentUiConfigId,
            LockSecondPasswordConfigId,
            UnlockSecondPasswordConfigId
        };
        if (requiredConfigIds.Any(id => !configs.ContainsKey(id)))
            throw new InvalidDataException("AA10 Item Lock content configuration is incomplete.");
        if (configs[UnlockDelayConfigId] <= 0 || configs[MoneyConfigId] < 0)
            throw new InvalidDataException("AA10 Item Lock delay or money cost is invalid.");

        _secureCategoryIds = secureCategories;
        _exceptionItemIds = exceptions;
        UnlockDelay = TimeSpan.FromMinutes(configs[UnlockDelayConfigId]);
        MoneyCost = configs[MoneyConfigId];
        UseEquipmentUi = configs[EquipmentUiConfigId] != 0;
        UseSecondPasswordWhenLocking = configs[LockSecondPasswordConfigId] != 0;
        UseSecondPasswordWhenUnlocking = configs[UnlockSecondPasswordConfigId] != 0;
    }

    public void PostLoad()
    {
    }
}
