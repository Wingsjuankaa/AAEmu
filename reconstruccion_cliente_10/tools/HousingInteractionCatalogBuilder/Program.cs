using System.Security.Cryptography;

using AAEmu.Game.GameData;
using AAEmu.Game.IO;
using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.Housing;

using Microsoft.Data.Sqlite;

using Newtonsoft.Json;

if (args.Length != 8)
{
    Console.Error.WriteLine(
        "Usage: HousingInteractionCatalogBuilder <full.sqlite3> <compact.sqlite3> <runtime.sqlite3> " +
        "<x2game.dll> <game_pak> <model-output.json> <binding-output.json> <manifest-output.json>");
    return 2;
}

var fullPath = Path.GetFullPath(args[0]);
var compactPath = Path.GetFullPath(args[1]);
var runtimePath = Path.GetFullPath(args[2]);
var x2GamePath = Path.GetFullPath(args[3]);
var gamePakPath = Path.GetFullPath(args[4]);
var modelOutputPath = Path.GetFullPath(args[5]);
var bindingOutputPath = Path.GetFullPath(args[6]);
var manifestOutputPath = Path.GetFullPath(args[7]);

foreach (var input in new[] { fullPath, compactPath, runtimePath, x2GamePath, gamePakPath })
{
    if (!File.Exists(input))
    {
        Console.Error.WriteLine($"Input does not exist: {input}");
        return 3;
    }
}

static SqliteConnection OpenReadOnly(string path)
{
    var connection = new SqliteConnection(
        new SqliteConnectionStringBuilder
        {
            DataSource = path,
            Mode = SqliteOpenMode.ReadOnly
        }.ToString());
    connection.Open();
    using var command = connection.CreateCommand();
    command.CommandText = "PRAGMA query_only=ON";
    command.ExecuteNonQuery();
    return connection;
}

static async Task<string> Sha256Async(string path)
{
    await using var stream = new FileStream(
        path, FileMode.Open, FileAccess.Read, FileShare.Read,
        bufferSize: 1024 * 1024, useAsync: true);
    return Convert.ToHexString(await SHA256.HashDataAsync(stream));
}

static bool ReadBool(SqliteDataReader reader, int ordinal)
{
    var value = reader.GetValue(ordinal);
    return value switch
    {
        bool boolean => boolean,
        long integer => integer != 0,
        string text => text.Equals("t", StringComparison.OrdinalIgnoreCase) ||
                       text.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                       text == "1",
        _ => false
    };
}

static List<(uint HousingId, byte AttachPointId, uint DoodadId, bool ForceDbSave)> LoadBindings(
    SqliteConnection connection)
{
    var rows = new List<(uint, byte, uint, bool)>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        SELECT housing_id, attach_point_id, doodad_id, force_db_save
        FROM housing_binding_doodads
        ORDER BY housing_id, attach_point_id, doodad_id
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
    {
        rows.Add((
            checked((uint)reader.GetInt64(0)),
            checked((byte)reader.GetInt64(1)),
            checked((uint)reader.GetInt64(2)),
            ReadBool(reader, 3)));
    }
    return rows;
}

static Dictionary<uint, uint> LoadHousingModels(SqliteConnection connection)
{
    var result = new Dictionary<uint, uint>();
    using var command = connection.CreateCommand();
    command.CommandText = "SELECT id, main_model_id FROM housings ORDER BY id";
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result[checked((uint)reader.GetInt64(0))] = checked((uint)reader.GetInt64(1));
    return result;
}

static Dictionary<uint, uint> LoadHousingCategories(SqliteConnection connection)
{
    var result = new Dictionary<uint, uint>();
    using var command = connection.CreateCommand();
    command.CommandText = "SELECT id, category_id FROM housings ORDER BY id";
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result[checked((uint)reader.GetInt64(0))] = checked((uint)reader.GetInt64(1));
    return result;
}

static Dictionary<uint, IReadOnlySet<string>> LoadDoodadFunctionTypes(SqliteConnection connection)
{
    var grouped = new Dictionary<uint, HashSet<string>>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        SELECT doodad_id, actual_func_type
        FROM (
            SELECT g.doodad_almighty_id AS doodad_id, f.actual_func_type
            FROM doodad_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            UNION
            SELECT g.doodad_almighty_id AS doodad_id, f.actual_func_type
            FROM doodad_phase_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
        )
        ORDER BY doodad_id, actual_func_type
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
    {
        var doodadId = checked((uint)reader.GetInt64(0));
        if (!grouped.TryGetValue(doodadId, out var types))
            grouped[doodadId] = types = new HashSet<string>(StringComparer.Ordinal);
        if (!reader.IsDBNull(1))
            types.Add(reader.GetString(1));
    }

    return grouped.ToDictionary(
        pair => pair.Key,
        pair => (IReadOnlySet<string>)pair.Value);
}

static HashSet<uint> LoadNativeCraftConsumerDoodadIds(SqliteConnection connection)
{
    var result = new HashSet<uint>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        SELECT DISTINCT g.doodad_almighty_id
        FROM doodad_func_groups g
        JOIN doodad_funcs f
          ON f.doodad_func_group_id = g.id
         AND f.actual_func_type = 'DoodadFuncCraftPack'
        JOIN doodad_func_craft_packs p ON p.id = f.actual_func_id
        JOIN craft_pack_crafts pc ON pc.craft_pack_id = p.craft_pack_id
        JOIN crafts c
          ON c.id = pc.craft_id
         AND c.enable = 't'
         AND c.req_doodad_id = g.doodad_almighty_id
        ORDER BY g.doodad_almighty_id
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result.Add(checked((uint)reader.GetInt64(0)));
    return result;
}

static HashSet<uint> LoadNativeWaterProviderDoodadIds(SqliteConnection connection)
{
    var result = new HashSet<uint>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        WITH water_loot AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            JOIN doodad_func_loot_items li ON li.id = f.actual_func_id
            JOIN items i ON i.id = li.item_id
            WHERE f.actual_func_type = 'DoodadFuncLootItem'
              AND li.item_id = 15694
              AND li.count_min > 0
              AND li.count_max >= li.count_min
              AND li.percent BETWEEN 1 AND 10000
        ),
        use_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            JOIN doodad_func_uses u ON u.id = f.actual_func_id
            JOIN skills s ON s.id = f.func_skill_id
            WHERE f.actual_func_type = 'DoodadFuncUse'
              AND f.func_skill_id > 0
        ),
        timer_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_phase_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            JOIN doodad_func_timers t ON t.id = f.actual_func_id
            WHERE f.actual_func_type = 'DoodadFuncTimer'
              AND t.delay >= 0
              AND t.next_phase > 0
        )
        SELECT water_loot.doodad_id
        FROM water_loot
        JOIN use_graph USING (doodad_id)
        JOIN timer_graph USING (doodad_id)
        ORDER BY water_loot.doodad_id
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result.Add(checked((uint)reader.GetInt64(0)));
    return result;
}

static HashSet<uint> KeepClosedWaterProviderFamily(
    IEnumerable<uint> candidates,
    IReadOnlyDictionary<uint, IReadOnlySet<string>> functionTypes)
{
    var requiredTypes = new HashSet<string>(StringComparer.Ordinal)
    {
        "DoodadFuncLootItem",
        "DoodadFuncTimer",
        "DoodadFuncUse"
    };

    return candidates
        .Where(id => functionTypes.TryGetValue(id, out var types) && types.SetEquals(requiredTypes))
        .ToHashSet();
}

static HashSet<uint> LoadNativePlanterDoodadIds(SqliteConnection connection)
{
    var result = new HashSet<uint>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        WITH ui_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            JOIN doodad_func_item_changer_ui_opens ui ON ui.id = f.actual_func_id
            WHERE f.actual_func_type = 'DoodadFuncItemChangerUiOpen'
        ),
        changer_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_phase_funcs pf
            JOIN doodad_func_groups g ON g.id = pf.doodad_func_group_id
            JOIN doodad_func_item_changers c ON c.id = pf.actual_func_id
            JOIN items i ON i.id = c.item_id
            JOIN skills s ON s.id = c.skill_id
            JOIN skill_effects se ON se.skill_id = s.id AND se.enable = 't'
            JOIN effects e ON e.id = se.effect_id AND e.actual_type = 'DoodadItemChangeEffect'
            JOIN doodad_item_change_effects ice ON ice.id = e.actual_id
            WHERE pf.actual_func_type = 'DoodadFuncItemChanger'
              AND c.item_count > 0
              AND c.next_phase > 0
        ),
        growth_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_phase_funcs pf
            JOIN doodad_func_groups g ON g.id = pf.doodad_func_group_id
            JOIN doodad_func_growths growth ON growth.id = pf.actual_func_id
            WHERE pf.actual_func_type = 'DoodadFuncGrowth'
              AND growth.delay >= 0
              AND growth.next_phase > 0
        ),
        timer_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_phase_funcs pf
            JOIN doodad_func_groups g ON g.id = pf.doodad_func_group_id
            JOIN doodad_func_timers timer ON timer.id = pf.actual_func_id
            WHERE pf.actual_func_type = 'DoodadFuncTimer'
              AND timer.delay >= 0
              AND timer.next_phase > 0
        ),
        harvest_graph AS (
            SELECT DISTINCT g.doodad_almighty_id AS doodad_id
            FROM doodad_funcs f
            JOIN doodad_func_groups g ON g.id = f.doodad_func_group_id
            JOIN doodad_func_loot_packs lp ON lp.id = f.actual_func_id
            JOIN loots l ON l.loot_pack_id = lp.loot_pack_id
            WHERE f.actual_func_type = 'DoodadFuncLootPack'
        )
        SELECT ui_graph.doodad_id
        FROM ui_graph
        JOIN changer_graph USING (doodad_id)
        JOIN growth_graph USING (doodad_id)
        JOIN timer_graph USING (doodad_id)
        JOIN harvest_graph USING (doodad_id)
        ORDER BY ui_graph.doodad_id
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result.Add(checked((uint)reader.GetInt64(0)));
    return result;
}

static HashSet<uint> KeepClosedPlanterFamily(
    IEnumerable<uint> candidates,
    IReadOnlyDictionary<uint, IReadOnlySet<string>> functionTypes,
    IReadOnlySet<uint> playFlowConsumers)
{
    var planterTypes = new HashSet<string>(StringComparer.Ordinal)
    {
        "DoodadFuncGrowth",
        "DoodadFuncItemChanger",
        "DoodadFuncItemChangerUiOpen",
        "DoodadFuncLootPack",
        "DoodadFuncRatioChange",
        "DoodadFuncTimer",
        "DoodadFuncUse"
    };
    var rancherPenTypes = planterTypes.ToHashSet(StringComparer.Ordinal);
    rancherPenTypes.Add("DoodadFuncPlayFlowGraph");

    return candidates
        .Where(id => functionTypes.TryGetValue(id, out var types) &&
                     (types.SetEquals(planterTypes) ||
                      (types.SetEquals(rancherPenTypes) && playFlowConsumers.Contains(id))))
        .ToHashSet();
}

static HashSet<uint> LoadNativePlayFlowConsumerDoodadIds(SqliteConnection connection)
{
    var result = new HashSet<uint>();
    using var command = connection.CreateCommand();
    command.CommandText = """
        SELECT DISTINCT g.doodad_almighty_id
        FROM doodad_phase_funcs pf
        JOIN doodad_func_groups g ON g.id = pf.doodad_func_group_id
        JOIN doodad_func_play_flow_graphs flow ON flow.id = pf.actual_func_id
        WHERE pf.actual_func_type = 'DoodadFuncPlayFlowGraph'
          AND flow.event_on_phase_change_id >= 0
          AND flow.event_on_visible_id >= 0
        ORDER BY g.doodad_almighty_id
        """;
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result.Add(checked((uint)reader.GetInt64(0)));
    return result;
}

static void RequireSameFunctionTypes(
    IReadOnlyDictionary<uint, IReadOnlySet<string>> full,
    IReadOnlyDictionary<uint, IReadOnlySet<string>> projected,
    string name)
{
    if (full.Count != projected.Count)
        throw new InvalidDataException($"{name} count differs between AA10 databases");

    foreach (var pair in full)
        if (!projected.TryGetValue(pair.Key, out var types) || !pair.Value.SetEquals(types))
            throw new InvalidDataException($"{name} differs for doodad {pair.Key}");
}

static HashSet<uint> LoadDoodadIds(SqliteConnection connection)
{
    var result = new HashSet<uint>();
    using var command = connection.CreateCommand();
    command.CommandText = "SELECT id FROM doodad_almighties ORDER BY id";
    using var reader = command.ExecuteReader();
    while (reader.Read())
        result.Add(checked((uint)reader.GetInt64(0)));
    return result;
}

static void RequireSame<T>(IReadOnlyList<T> full, IReadOnlyList<T> projected, string name)
{
    if (full.Count != projected.Count || !full.SequenceEqual(projected))
        throw new InvalidDataException($"{name} differs between full and projected AA10 databases");
}

using var full = OpenReadOnly(fullPath);
using var compact = OpenReadOnly(compactPath);
using var runtime = OpenReadOnly(runtimePath);

var fullBindings = LoadBindings(full);
RequireSame(fullBindings, LoadBindings(compact), "housing_binding_doodads/full-compact");
RequireSame(fullBindings, LoadBindings(runtime), "housing_binding_doodads/full-runtime");

var fullModels = LoadHousingModels(full);
var compactModels = LoadHousingModels(compact);
var runtimeModels = LoadHousingModels(runtime);
if (!fullModels.OrderBy(x => x.Key).SequenceEqual(compactModels.OrderBy(x => x.Key)) ||
    !fullModels.OrderBy(x => x.Key).SequenceEqual(runtimeModels.OrderBy(x => x.Key)))
    throw new InvalidDataException("housings.main_model_id differs between full, compact or runtime AA10");

var fullCategories = LoadHousingCategories(full);
if (!fullCategories.OrderBy(x => x.Key).SequenceEqual(LoadHousingCategories(compact).OrderBy(x => x.Key)) ||
    !fullCategories.OrderBy(x => x.Key).SequenceEqual(LoadHousingCategories(runtime).OrderBy(x => x.Key)))
    throw new InvalidDataException("housings.category_id differs between full, compact or runtime AA10");

var fullFunctionTypes = LoadDoodadFunctionTypes(full);
var compactFunctionTypes = LoadDoodadFunctionTypes(compact);
var runtimeFunctionTypes = LoadDoodadFunctionTypes(runtime);
RequireSameFunctionTypes(fullFunctionTypes, compactFunctionTypes, "doodad function types/full-compact");
RequireSameFunctionTypes(fullFunctionTypes, runtimeFunctionTypes, "doodad function types/full-runtime");

var fullNativeCraftConsumers = LoadNativeCraftConsumerDoodadIds(full);
var compactNativeCraftConsumers = LoadNativeCraftConsumerDoodadIds(compact);
var runtimeNativeCraftConsumers = LoadNativeCraftConsumerDoodadIds(runtime);
var provenNativeCraftConsumers = fullNativeCraftConsumers
    .Intersect(compactNativeCraftConsumers)
    .Intersect(runtimeNativeCraftConsumers)
    .ToHashSet();
var craftConsumerProjectionMismatches = fullNativeCraftConsumers
    .Union(compactNativeCraftConsumers)
    .Union(runtimeNativeCraftConsumers)
    .Except(provenNativeCraftConsumers)
    .Order()
    .ToArray();

var fullNativeWaterProviders = KeepClosedWaterProviderFamily(
    LoadNativeWaterProviderDoodadIds(full), fullFunctionTypes);
var compactNativeWaterProviders = KeepClosedWaterProviderFamily(
    LoadNativeWaterProviderDoodadIds(compact), compactFunctionTypes);
var runtimeNativeWaterProviders = KeepClosedWaterProviderFamily(
    LoadNativeWaterProviderDoodadIds(runtime), runtimeFunctionTypes);
var provenNativeWaterProviders = fullNativeWaterProviders
    .Intersect(compactNativeWaterProviders)
    .Intersect(runtimeNativeWaterProviders)
    .ToHashSet();
var waterProviderProjectionMismatches = fullNativeWaterProviders
    .Union(compactNativeWaterProviders)
    .Union(runtimeNativeWaterProviders)
    .Except(provenNativeWaterProviders)
    .Order()
    .ToArray();

var fullNativePlanters = KeepClosedPlanterFamily(
    LoadNativePlanterDoodadIds(full), fullFunctionTypes, LoadNativePlayFlowConsumerDoodadIds(full));
var compactNativePlanters = KeepClosedPlanterFamily(
    LoadNativePlanterDoodadIds(compact), compactFunctionTypes, LoadNativePlayFlowConsumerDoodadIds(compact));
var runtimeNativePlanters = KeepClosedPlanterFamily(
    LoadNativePlanterDoodadIds(runtime), runtimeFunctionTypes, LoadNativePlayFlowConsumerDoodadIds(runtime));
var provenNativePlanters = fullNativePlanters
    .Intersect(compactNativePlanters)
    .Intersect(runtimeNativePlanters)
    .ToHashSet();
var planterProjectionMismatches = fullNativePlanters
    .Union(compactNativePlanters)
    .Union(runtimeNativePlanters)
    .Except(provenNativePlanters)
    .Order()
    .ToArray();

ClientFileManager.ClearSources();
if (!ClientFileManager.AddSource(gamePakPath))
    throw new InvalidDataException("Could not open game_pak read-only");

var modelBuilder = new ModelAttachPointGameData();
var modelCatalog = modelBuilder.BuildFromClientData(full);
ClientFileManager.ClearSources();

var doodadIds = LoadDoodadIds(full);
var definitions = new List<HousingBindingDefinition>(fullBindings.Count);
foreach (var row in fullBindings)
{
    var reason = HousingInteractionBlockReason.None;
    HousingLocalTransform? transform = null;
    var source = HousingBindingPositionSource.None;

    if (!fullModels.TryGetValue(row.HousingId, out var modelId))
        reason = HousingInteractionBlockReason.MissingHousingTemplate;
    else if (!doodadIds.Contains(row.DoodadId))
        reason = HousingInteractionBlockReason.MissingDoodadTemplate;
    else if (!modelCatalog.Models.TryGetValue(modelId, out var points))
        reason = HousingInteractionBlockReason.MissingModel;
    else if (!points.TryGetValue((AttachPointKind)row.AttachPointId, out transform))
        reason = HousingInteractionBlockReason.MissingPosition;
    else if (!transform.IsFinite || !transform.HasUniformScale())
        reason = HousingInteractionBlockReason.InvalidTransform;
    else
    {
        source = HousingBindingPositionSource.Aa10ModelHelper;
        var functionTypes = fullFunctionTypes.GetValueOrDefault(
            row.DoodadId,
            (IReadOnlySet<string>)new HashSet<string>(StringComparer.Ordinal));
        reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            fullCategories[row.HousingId],
            (AttachPointKind)row.AttachPointId,
            functionTypes,
            provenNativeCraftConsumers.Contains(row.DoodadId),
            provenNativeWaterProviders.Contains(row.DoodadId),
            provenNativePlanters.Contains(row.DoodadId));
    }

    definitions.Add(new HousingBindingDefinition
    {
        HousingTemplateId = row.HousingId,
        AttachPointId = (AttachPointKind)row.AttachPointId,
        DoodadId = row.DoodadId,
        ForceDbSave = row.ForceDbSave,
        PersistMutableState = reason == HousingInteractionBlockReason.None &&
                              provenNativePlanters.Contains(row.DoodadId),
        Transform = transform,
        PositionSource = source,
        BlockReason = reason
    });
}

var fullHash = await Sha256Async(fullPath);
var compactHash = await Sha256Async(compactPath);
var runtimeHash = await Sha256Async(runtimePath);
var x2GameHash = await Sha256Async(x2GamePath);
var gamePakHash = await Sha256Async(gamePakPath);

var interactionFile = new HousingInteractionCatalogFile
{
    SchemaVersion = HousingInteractionCatalog.CurrentSchemaVersion,
    ClientBuild = "10.0.2.13-r575",
    FullSha256 = fullHash,
    CompactSha256 = compactHash,
    X2GameSha256 = x2GameHash,
    Bindings = definitions
};

var jsonSettings = new JsonSerializerSettings
{
    Formatting = Formatting.Indented,
    NullValueHandling = NullValueHandling.Ignore
};

foreach (var output in new[] { modelOutputPath, bindingOutputPath, manifestOutputPath })
    Directory.CreateDirectory(Path.GetDirectoryName(output)!);

await File.WriteAllTextAsync(modelOutputPath, JsonConvert.SerializeObject(modelCatalog, jsonSettings) + Environment.NewLine);
await File.WriteAllTextAsync(bindingOutputPath, JsonConvert.SerializeObject(interactionFile, jsonSettings) + Environment.NewLine);

var blockCounts = definitions
    .GroupBy(x => x.BlockReason)
    .OrderBy(x => x.Key)
    .ToDictionary(x => x.Key.ToString(), x => x.Count());
var promotedResidentialWaterProviders = definitions
    .Where(x => x.IsExecutable && provenNativeWaterProviders.Contains(x.DoodadId))
    .Select(x => x.DoodadId)
    .Distinct()
    .Order()
    .ToArray();
var promotedResidentialPlanters = definitions
    .Where(x => x.IsExecutable && provenNativePlanters.Contains(x.DoodadId))
    .Select(x => x.DoodadId)
    .Distinct()
    .Order()
    .ToArray();
var manifest = new
{
    schema_version = 1,
    wave = "AA10 native Housing H5-B residential water providers and planter beds",
    client_build = "10.0.2.13-r575",
    inputs = new
    {
        full = new { path = fullPath, sha256 = fullHash },
        compact = new { path = compactPath, sha256 = compactHash },
        runtime = new { path = runtimePath, sha256 = runtimeHash },
        x2game = new { path = x2GamePath, sha256 = x2GameHash },
        game_pak = new { path = gamePakPath, sha256 = gamePakHash }
    },
    metrics = new
    {
        housing_templates = fullModels.Count,
        binding_rows = definitions.Count,
        binding_housing_templates = definitions.Select(x => x.HousingTemplateId).Distinct().Count(),
        doodad_templates = definitions.Select(x => x.DoodadId).Distinct().Count(),
        attach_points = definitions.Select(x => x.AttachPointId).Distinct().Count(),
        model_sets = modelCatalog.Models.Count,
        executable = definitions.Count(x => x.IsExecutable),
        force_db_save = definitions.Count(x => x.ForceDbSave),
        persist_mutable_state = definitions.Count(x => x.PersistMutableState),
        blocked = definitions.Count(x => !x.IsExecutable),
        block_reasons = blockCounts,
        craft_consumer_projection_mismatches = craftConsumerProjectionMismatches,
        native_water_provider_consumers = provenNativeWaterProviders.Order().ToArray(),
        promoted_residential_water_provider_doodads = promotedResidentialWaterProviders,
        promoted_residential_water_provider_bindings = definitions.Count(x =>
            x.IsExecutable && promotedResidentialWaterProviders.Contains(x.DoodadId)),
        water_provider_projection_mismatches = waterProviderProjectionMismatches,
        native_planter_consumers = provenNativePlanters.Order().ToArray(),
        promoted_residential_planter_doodads = promotedResidentialPlanters,
        promoted_residential_planter_bindings = definitions.Count(x =>
            x.IsExecutable && promotedResidentialPlanters.Contains(x.DoodadId)),
        promoted_residential_planter_templates = definitions
            .Where(x => x.IsExecutable && promotedResidentialPlanters.Contains(x.DoodadId))
            .Select(x => x.HousingTemplateId)
            .Distinct()
            .Count(),
        planter_projection_mismatches = planterProjectionMismatches
    },
    stone_rose_manor = definitions.Where(x => x.HousingTemplateId == 313).ToArray(),
    tradesmans_manor = definitions.Where(x => x.HousingTemplateId == 437).ToArray(),
    thatched_farmhouse = definitions.Where(x => x.HousingTemplateId == 330).ToArray(),
    upgraded_thatched_farmhouse = definitions.Where(x => x.HousingTemplateId == 434).ToArray(),
    constraints = new
    {
        aa8_values_copied = 0,
        legacy_housing_bindings_used = false,
        implicit_zero_fallback = false,
        runtime_game_pak_scan = false
    }
};
await File.WriteAllTextAsync(manifestOutputPath, JsonConvert.SerializeObject(manifest, jsonSettings) + Environment.NewLine);

Console.WriteLine($"models={modelCatalog.Models.Count}");
Console.WriteLine($"bindings={definitions.Count}");
Console.WriteLine($"executable={definitions.Count(x => x.IsExecutable)}");
Console.WriteLine($"blocked={definitions.Count(x => !x.IsExecutable)}");
Console.WriteLine($"stone_rose={definitions.Count(x => x.HousingTemplateId == 313 && x.IsExecutable)}/5");
Console.WriteLine($"tradesmans_manor={definitions.Count(x => x.HousingTemplateId == 437 && x.IsExecutable)}/10");
Console.WriteLine($"thatched_farmhouse={definitions.Count(x => x.HousingTemplateId == 330 && x.IsExecutable)}/6");
Console.WriteLine($"water_providers={promotedResidentialWaterProviders.Length}/8 doodads, {definitions.Count(x => x.IsExecutable && promotedResidentialWaterProviders.Contains(x.DoodadId))}/25 bindings");
Console.WriteLine($"planters={promotedResidentialPlanters.Length}/1 doodads, {definitions.Count(x => x.IsExecutable && promotedResidentialPlanters.Contains(x.DoodadId))}/73 bindings, {definitions.Where(x => x.IsExecutable && promotedResidentialPlanters.Contains(x.DoodadId)).Select(x => x.HousingTemplateId).Distinct().Count()}/37 templates");
return 0;
