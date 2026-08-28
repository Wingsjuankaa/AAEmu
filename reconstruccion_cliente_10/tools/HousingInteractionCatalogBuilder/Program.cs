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
        // H3 promotes only the five structural bindings whose AA10 consumers are
        // part of its retail gate. Geometry readiness is not consumer readiness:
        // H4/H5 will explicitly promote the remaining residential families.
        if (row.HousingId != 313)
            reason = HousingInteractionBlockReason.PendingWavePromotion;
    }

    definitions.Add(new HousingBindingDefinition
    {
        HousingTemplateId = row.HousingId,
        AttachPointId = (AttachPointKind)row.AttachPointId,
        DoodadId = row.DoodadId,
        ForceDbSave = row.ForceDbSave,
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
var manifest = new
{
    schema_version = 1,
    wave = "AA10 native Housing H3",
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
        blocked = definitions.Count(x => !x.IsExecutable),
        block_reasons = blockCounts
    },
    stone_rose_manor = definitions.Where(x => x.HousingTemplateId == 313).ToArray(),
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
return 0;
