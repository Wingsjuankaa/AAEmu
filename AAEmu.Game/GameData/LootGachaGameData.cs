using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData;

/// <summary>Native AA10 r575 Loot Gacha catalogue.</summary>
[GameData]
public sealed class LootGachaGameData : Singleton<LootGachaGameData>, IGameDataLoader
{
    private Dictionary<uint, LootGachaPackDefinition> _packs = [];
    private Dictionary<(uint SourceItemId, uint ConsumeItemId), LootGachaPackDefinition> _byItems = [];

    public int PackCount => _packs.Count;
    public int ItemMappingCount => _packs.Values.Sum(pack => pack.SourceItemIds.Count + pack.ConsumeItemIds.Count);
    public int AdvancedPackCount => _packs.Values.Sum(pack => pack.AdvancedPacks.Count);

    public void Load(SqliteConnection connection)
    {
        ArgumentNullException.ThrowIfNull(connection);
        var packs = new Dictionary<uint, LootGachaPackDefinition>();

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT id, loot_pack_id, active FROM gacha_loot_packs";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var pack = new LootGachaPackDefinition
                {
                    Id = reader.GetUInt32("id"),
                    LootPackId = reader.GetUInt32("loot_pack_id"),
                    Active = reader.GetBoolean("active")
                };
                packs.Add(pack.Id, pack);
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT gacha_loot_pack_id, kind, item_id FROM gacha_loot_pack_items";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                if (!packs.TryGetValue(reader.GetUInt32("gacha_loot_pack_id"), out var pack))
                    throw new InvalidDataException("Loot Gacha item mapping references a missing pack.");
                var destination = reader.GetInt32("kind") == 0
                    ? pack.SourceItemIds
                    : pack.ConsumeItemIds;
                destination.Add(reader.GetUInt32("item_id"));
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT id, gacha_loot_pack_id, add_round, give_term, loot_pack_id, rate, priority " +
                "FROM gacha_advanced_loot_packs";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var gachaPackId = reader.GetUInt32("gacha_loot_pack_id");
                if (!packs.TryGetValue(gachaPackId, out var pack))
                    throw new InvalidDataException("Advanced Loot Gacha row references a missing pack.");
                pack.AdvancedPacks.Add(new LootGachaAdvancedDefinition
                {
                    Id = reader.GetUInt32("id"),
                    GachaLootPackId = gachaPackId,
                    AddRound = reader.GetUInt32("add_round"),
                    GiveTerm = reader.GetUInt32("give_term"),
                    LootPackId = reader.GetUInt32("loot_pack_id"),
                    Rate = reader.GetUInt32("rate"),
                    Priority = reader.GetUInt32("priority")
                });
            }
        }

        if (packs.Count != 11 || packs.Values.Sum(pack =>
                pack.SourceItemIds.Count + pack.ConsumeItemIds.Count) != 24 ||
            packs.Values.Sum(pack => pack.AdvancedPacks.Count) != 30)
            throw new InvalidDataException(
                "AA10 Loot Gacha catalogue does not match the native 11/24/30 row contract.");
        if (packs.Values.Any(pack => pack.SourceItemIds.Count == 0 || pack.LootPackId == 0))
            throw new InvalidDataException("AA10 Loot Gacha contains an incomplete pack.");

        var byItems = new Dictionary<(uint, uint), LootGachaPackDefinition>();
        foreach (var pack in packs.Values.Where(pack => pack.Active))
        foreach (var source in pack.SourceItemIds)
        {
            if (pack.ConsumeItemIds.Count == 0)
                byItems.Add((source, 0), pack);
            else
                foreach (var consume in pack.ConsumeItemIds)
                    byItems.Add((source, consume), pack);
        }

        _packs = packs;
        _byItems = byItems;
    }

    public void PostLoad()
    {
    }

    public bool TryGetActivePack(uint sourceItemId, uint consumeItemId, out LootGachaPackDefinition pack) =>
        _byItems.TryGetValue((sourceItemId, consumeItemId), out pack);

    public LootGachaPackDefinition GetPack(uint id) => _packs.GetValueOrDefault(id);

}

public sealed class LootGachaPackDefinition
{
    public uint Id { get; init; }
    public uint LootPackId { get; init; }
    public bool Active { get; init; }
    public List<uint> SourceItemIds { get; } = [];
    public List<uint> ConsumeItemIds { get; } = [];
    public List<LootGachaAdvancedDefinition> AdvancedPacks { get; } = [];
}

public sealed class LootGachaAdvancedDefinition
{
    public uint Id { get; init; }
    public uint GachaLootPackId { get; init; }
    public uint AddRound { get; init; }
    public uint GiveTerm { get; init; }
    public uint LootPackId { get; init; }
    public uint Rate { get; init; }
    public uint Priority { get; init; }
}
