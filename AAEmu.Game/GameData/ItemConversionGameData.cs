using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData;

/// <summary>
/// Loads the complete AA10 item-conversion graph. Reagent-pack and product-pack identifiers are
/// independent namespaces; both must be traversed through their item-conversion member tables.
/// </summary>
[GameData]
public class ItemConversionGameData : Singleton<ItemConversionGameData>, IGameDataLoader
{
    private Dictionary<uint, ItemConversionRoute> _routes = [];
    private Dictionary<int, List<ItemConversionRoute>> _routesBySet = [];

    public void Load(SqliteConnection connection)
    {
        _routes = [];
        _routesBySet = [];

        LoadRoutes(connection);
        var routesByReagentPack = LoadReagentPackMembers(connection);
        LoadExplicitReagents(connection, routesByReagentPack);
        LoadReagentFilters(connection, routesByReagentPack);
        LoadProductGraph(connection);

        foreach (var route in _routes.Values.OrderBy(route => route.Id))
        {
            if (!_routesBySet.TryGetValue(route.SetId, out var routes))
            {
                routes = [];
                _routesBySet.Add(route.SetId, routes);
            }

            routes.Add(route);
        }
    }

    public void PostLoad()
    {
    }

    public ItemConversionResolution Resolve(
        int conversionSetId,
        byte grade,
        ItemImplEnum implId,
        uint itemId,
        int level,
        Func<int, int> next = null)
    {
        if (!_routesBySet.TryGetValue(conversionSetId, out var routes))
            return ItemConversionResolution.Failure($"Unknown item conversion set {conversionSetId}.");

        // Exact catalogue entries have precedence over broad implementation/level filters. Ambiguous
        // catalogue rows are rejected: selecting the first route would silently convert into the
        // wrong product when another request parameter is still unknown.
        var matchingRoutes = routes.Where(candidate => candidate.Reagents.Any(reagent =>
            reagent.IsExplicit && reagent.Matches(grade, implId, itemId, level))).ToArray();
        if (matchingRoutes.Length == 0)
            matchingRoutes = routes.Where(candidate => candidate.Reagents.Any(reagent =>
                !reagent.IsExplicit && reagent.Matches(grade, implId, itemId, level))).ToArray();
        if (matchingRoutes.Length == 0)
            return ItemConversionResolution.Failure(
                $"Item {itemId} grade {grade} level {level} is not a reagent of conversion set {conversionSetId}.");
        if (matchingRoutes.Length > 1)
            return ItemConversionResolution.Failure(
                $"Item {itemId} matches multiple routes in conversion set {conversionSetId}: " +
                string.Join(",", matchingRoutes.Select(candidate => candidate.Id)) + ".");

        var route = matchingRoutes[0];

        if (route.ProductPacks.Count == 0)
            return ItemConversionResolution.Failure($"Conversion route {route.Id} has no product packs.");

        next ??= Random.Shared.Next;
        var rewards = new List<ItemConversionReward>();
        foreach (var pack in route.ProductPacks)
        {
            if (pack.Products.Count == 0)
                return ItemConversionResolution.Failure($"Product pack {pack.Id} has no products.");

            var chance = Math.Clamp(pack.ChanceRate, 0, 10_000);
            if (chance < 10_000 && next(10_000) >= chance)
                continue;

            var product = PickWeighted(pack.Products, next);
            if (product is null || product.MinOutput <= 0 || product.MaxOutput < product.MinOutput)
                return ItemConversionResolution.Failure($"Product pack {pack.Id} has an invalid product range.");

            var amount = product.MinOutput == product.MaxOutput
                ? product.MinOutput
                : product.MinOutput + next(checked(product.MaxOutput - product.MinOutput + 1));
            rewards.Add(new ItemConversionReward(product.OutputItemId, amount, product.GradeId));
        }

        return new ItemConversionResolution
        {
            IsValid = true,
            Route = route,
            Rewards = rewards
        };
    }

    private void LoadRoutes(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, name, item_conv_set_id FROM item_convs";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);
        while (reader.Read())
        {
            var route = new ItemConversionRoute
            {
                Id = reader.GetUInt32("id"),
                Name = reader.GetString("name"),
                SetId = reader.GetInt32("item_conv_set_id", -1)
            };
            _routes[route.Id] = route;
        }
    }

    private Dictionary<uint, List<ItemConversionRoute>> LoadReagentPackMembers(SqliteConnection connection)
    {
        var routesByPack = new Dictionary<uint, List<ItemConversionRoute>>();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT item_conv_id, item_conv_rpack_id FROM item_conv_rpack_members ORDER BY id";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);
        while (reader.Read())
        {
            var routeId = reader.GetUInt32("item_conv_id");
            var packId = reader.GetUInt32("item_conv_rpack_id");
            if (!_routes.TryGetValue(routeId, out var route))
                continue;
            if (!routesByPack.TryGetValue(packId, out var routes))
            {
                routes = [];
                routesByPack.Add(packId, routes);
            }
            routes.Add(route);
        }

        return routesByPack;
    }

    private static void LoadExplicitReagents(
        SqliteConnection connection,
        IReadOnlyDictionary<uint, List<ItemConversionRoute>> routesByPack)
    {
        using var command = connection.CreateCommand();
        command.CommandText =
            "SELECT item_conv_rpack_id, item_id, grade_id, max_grade_id FROM item_conv_reagents ORDER BY id";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);
        while (reader.Read())
        {
            var packId = reader.GetUInt32("item_conv_rpack_id");
            if (!routesByPack.TryGetValue(packId, out var routes))
                continue;
            var reagent = new ItemConversionReagent
            {
                ReagentPackId = packId,
                InputItemId = reader.GetUInt32("item_id"),
                MinItemGrade = reader.GetByte("grade_id", 1),
                MaxItemGrade = reader.GetByte("max_grade_id", 0)
            };
            foreach (var route in routes)
                route.Reagents.Add(reagent);
        }
    }

    private static void LoadReagentFilters(
        SqliteConnection connection,
        IReadOnlyDictionary<uint, List<ItemConversionRoute>> routesByPack)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM item_conv_reagent_filters ORDER BY id";
        command.Prepare();
        using var sqliteReader = command.ExecuteReader();
        using var reader = new SQLiteWrapperReader(sqliteReader);
        while (reader.Read())
        {
            // AA10 has epack-only filters whose rpack is NULL. They do not participate here.
            var packId = reader.GetUInt32("item_conv_rpack_id", 0);
            if (packId == 0 || !routesByPack.TryGetValue(packId, out var routes))
                continue;
            var reagent = new ItemConversionReagent
            {
                ReagentPackId = packId,
                ImplId = (ItemImplEnum)reader.GetInt32("item_impl_id"),
                MinLevel = reader.GetInt32("min_level"),
                MaxLevel = reader.GetInt32("max_level"),
                MinItemGrade = reader.GetByte("item_grade_id", 0),
                MaxItemGrade = reader.GetByte("max_item_grade_id", 0)
            };
            foreach (var route in routes)
                route.Reagents.Add(reagent);
        }
    }

    private void LoadProductGraph(SqliteConnection connection)
    {
        var packs = new Dictionary<uint, ItemConversionProductPack>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT id, chance_rate FROM item_conv_ppacks";
            command.Prepare();
            using var sqliteReader = command.ExecuteReader();
            using var reader = new SQLiteWrapperReader(sqliteReader);
            while (reader.Read())
            {
                var pack = new ItemConversionProductPack
                {
                    Id = reader.GetUInt32("id"),
                    ChanceRate = reader.GetInt32("chance_rate", 10_000)
                };
                packs[pack.Id] = pack;
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM item_conv_products ORDER BY id";
            command.Prepare();
            using var sqliteReader = command.ExecuteReader();
            using var reader = new SQLiteWrapperReader(sqliteReader);
            while (reader.Read())
            {
                var packId = reader.GetUInt32("item_conv_ppack_id");
                if (!packs.TryGetValue(packId, out var pack))
                    continue;
                pack.Products.Add(new ItemConversionProduct
                {
                    ProductPackId = packId,
                    OutputItemId = reader.GetUInt32("item_id"),
                    Weight = reader.GetInt32("weight", 1),
                    MinOutput = reader.GetInt32("min", 1),
                    MaxOutput = reader.GetInt32("max", 1),
                    GradeId = reader.GetInt32("item_grade_id", -1)
                });
            }
        }

        using var memberCommand = connection.CreateCommand();
        memberCommand.CommandText = "SELECT item_conv_id, item_conv_ppack_id FROM item_conv_ppack_members ORDER BY id";
        memberCommand.Prepare();
        using var memberSqliteReader = memberCommand.ExecuteReader();
        using var memberReader = new SQLiteWrapperReader(memberSqliteReader);
        while (memberReader.Read())
        {
            var routeId = memberReader.GetUInt32("item_conv_id");
            var packId = memberReader.GetUInt32("item_conv_ppack_id");
            if (_routes.TryGetValue(routeId, out var route) && packs.TryGetValue(packId, out var pack))
                route.ProductPacks.Add(pack);
        }
    }

    private static ItemConversionProduct PickWeighted(
        IReadOnlyList<ItemConversionProduct> products,
        Func<int, int> next)
    {
        long total = 0;
        foreach (var product in products)
            total += Math.Max(0, product.Weight);
        if (total <= 0 || total > int.MaxValue)
            return null;

        var roll = next((int)total);
        long running = 0;
        foreach (var product in products)
        {
            running += Math.Max(0, product.Weight);
            if (roll < running)
                return product;
        }

        return products[^1];
    }
}
