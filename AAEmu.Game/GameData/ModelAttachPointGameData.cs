using System.Numerics;
using System.Xml.Linq;

using AAEmu.Commons.IO;
using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.IO;
using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

using Newtonsoft.Json;

using NLog;

namespace AAEmu.Game.GameData;

/// <summary>
/// Attach point offsets for every model housing and slaves bind doodads to, resolved from the client's own
/// data instead of a hand-kept table.
///
/// The chain is entirely in the shipped data:
///   models.sub_id + sub_type  →  prefab_elements.file_path (PrefabModel) or
///                                ship_models.normal / vehicle_models.normal (Ship/VehicleModel)
///                             →  prefab://prefabs/&lt;lib&gt;.xml/&lt;prefab&gt;  →  game/prefabs/&lt;lib&gt;.xml
///                             →  &lt;Object Type="Brush" Prefab="…cgf"&gt;
///                             →  that cgf's '$' helper nodes, named by model_attach_point_strings.prefab
///
/// Reading ~900 meshes out of a 68 GB game_pak is not something to repeat every boot, so the resolved table
/// is cached next to the other client data and rebuilt only when the pak changes.
/// </summary>
[GameData]
public class ModelAttachPointGameData : Singleton<ModelAttachPointGameData>, IGameDataLoader
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    public const string CatalogFileName = "model_attach_points_aa10_h3.json";

    private Dictionary<uint, Dictionary<AttachPointKind, WorldSpawnPosition>> _attachPoints = [];
    private Dictionary<uint, Dictionary<AttachPointKind, HousingLocalTransform>> _transforms = [];

    /// <summary>Attach point id → the '$' helper name that carries it in a mesh.</summary>
    private Dictionary<AttachPointKind, string> _helperNames = [];

    /// <summary>Parsed prefab libraries, held only while the cache is being built.</summary>
    private readonly Dictionary<string, Dictionary<string, List<(string Mesh, Matrix4x4 Transform)>>> _prefabMeshCache =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Helper nodes per mesh; scenery meshes repeat across prefabs, so they are only read once.</summary>
    private readonly Dictionary<string, Dictionary<string, CgfHelperTransform>> _meshHelperCache =
        new(StringComparer.OrdinalIgnoreCase);

    public bool HasData => _attachPoints.Count > 0;

    public void Load(SqliteConnection connection)
    {
        _attachPoints = [];
        _transforms = [];

        var path = Path.Combine(FileManager.AppPath, "Data", CatalogFileName);
        if (!File.Exists(path))
        {
            Logger.Error("AA10 model attach-point catalogue is missing; model bindings will fail closed.");
            return;
        }

        try
        {
            var catalog = JsonConvert.DeserializeObject<ModelAttachPointCatalogFile>(File.ReadAllText(path));
            if (catalog?.SchemaVersion != ModelAttachPointCatalogFile.CurrentSchemaVersion ||
                catalog.Models == null || catalog.Models.Count == 0)
            {
                Logger.Error("AA10 model attach-point catalogue is invalid; model bindings will fail closed.");
                return;
            }

            _transforms = catalog.Models;
            foreach (var (modelId, points) in _transforms)
            {
                var projected = new Dictionary<AttachPointKind, WorldSpawnPosition>();
                foreach (var (attachPoint, transform) in points)
                {
                    if (transform is { IsFinite: true })
                        projected[attachPoint] = transform.ToWorldSpawnPosition();
                }

                if (projected.Count > 0)
                    _attachPoints[modelId] = projected;
            }

            Logger.Info($"Loaded {_attachPoints.Count} model attach point sets from deterministic AA10 catalogue");
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Could not load AA10 model attach-point catalogue; model bindings fail closed.");
        }
    }

    public void PostLoad()
    {
        // Nothing to resolve here; consumers read the table in their own PostLoad.
    }

    public ModelAttachPointCatalogFile BuildFromClientData(SqliteConnection connection)
    {
        ArgumentNullException.ThrowIfNull(connection);

        _helperNames = LoadHelperNames(connection);
        if (_helperNames.Count == 0)
            throw new InvalidDataException("model_attach_point_strings is empty");

        _prefabMeshCache.Clear();
        _meshHelperCache.Clear();
        var result = new Dictionary<uint, Dictionary<AttachPointKind, HousingLocalTransform>>();

        foreach (var modelId in LoadModelsOfInterest(connection))
        {
            var brushes = ResolveMeshes(connection, modelId);
            if (brushes.Count == 0)
                continue;

            var helpers = new Dictionary<string, HousingLocalTransform>(StringComparer.OrdinalIgnoreCase);
            foreach (var (meshPath, brushTransform) in brushes)
            {
                foreach (var (name, local) in ReadMeshHelpers(meshPath))
                {
                    var combined = local.ToMatrix() * brushTransform;
                    if (!Matrix4x4.Decompose(combined, out var scale, out var rotation, out var position))
                        continue;

                    var transform = new HousingLocalTransform
                    {
                        X = position.X,
                        Y = position.Y,
                        Z = position.Z,
                        RotationX = rotation.X,
                        RotationY = rotation.Y,
                        RotationZ = rotation.Z,
                        RotationW = rotation.W,
                        ScaleX = scale.X,
                        ScaleY = scale.Y,
                        ScaleZ = scale.Z
                    };
                    if (transform.IsFinite)
                        helpers.TryAdd(name, transform);
                }
            }

            var points = new Dictionary<AttachPointKind, HousingLocalTransform>();
            foreach (var (attachPoint, helperName) in _helperNames)
            {
                if (helpers.TryGetValue(helperName, out var transform))
                    points[attachPoint] = transform;
            }

            if (points.Count > 0)
                result[modelId] = points;
        }

        _prefabMeshCache.Clear();
        _meshHelperCache.Clear();
        return new ModelAttachPointCatalogFile { Models = result };
    }

    /// <summary>Attach points for a model, or null when the model has none.</summary>
    public Dictionary<AttachPointKind, WorldSpawnPosition> GetAttachPoints(uint modelId)
    {
        return _attachPoints.GetValueOrDefault(modelId);
    }

    /// <summary>Single attach point for a model, or null.</summary>
    public WorldSpawnPosition GetAttachPoint(uint modelId, AttachPointKind attachPoint)
    {
        var set = _attachPoints.GetValueOrDefault(modelId);
        return set != null && set.TryGetValue(attachPoint, out var pos) ? pos : null;
    }

    public HousingLocalTransform GetAttachPointTransform(uint modelId, AttachPointKind attachPoint)
    {
        var set = _transforms.GetValueOrDefault(modelId);
        return set != null && set.TryGetValue(attachPoint, out var transform) ? transform : null;
    }

    private static Dictionary<AttachPointKind, string> LoadHelperNames(SqliteConnection connection)
    {
        var res = new Dictionary<AttachPointKind, string>();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, prefab FROM model_attach_point_strings";
        command.Prepare();
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
        {
            var prefab = reader.GetString("prefab", string.Empty);
            if (string.IsNullOrWhiteSpace(prefab) || !prefab.StartsWith('$'))
                continue;
            res[(AttachPointKind)reader.GetInt16("id")] = prefab;
        }
        return res;
    }

    /// <summary>Every model housing or a slave can bind something to — the only ones worth resolving.</summary>
    private static List<uint> LoadModelsOfInterest(SqliteConnection connection)
    {
        var ids = new HashSet<uint>();

        void Collect(string sql)
        {
            using var command = connection.CreateCommand();
            command.CommandText = sql;
            command.Prepare();
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var id = reader.GetUInt32("model_id", 0);
                if (id > 0)
                    ids.Add(id);
            }
        }

        Collect("SELECT DISTINCT main_model_id AS model_id FROM housings");
        Collect("SELECT DISTINCT model_id FROM housing_build_steps");
        Collect("SELECT DISTINCT model_id FROM slaves");

        return [.. ids.Order()];
    }

    /// <summary>
    /// models → every cgf in the model's completed state, with its full prefab transform.
    /// </summary>
    private List<(string Mesh, Matrix4x4 Transform)> ResolveMeshes(SqliteConnection connection, uint modelId)
    {
        string subType = null;
        var subId = 0u;
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT sub_id, sub_type FROM models WHERE id=@id";
            command.Parameters.AddWithValue("@id", modelId);
            command.Prepare();
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            if (reader.Read())
            {
                subId = reader.GetUInt32("sub_id", 0);
                subType = reader.GetString("sub_type", string.Empty);
            }
        }

        if (subId == 0 || string.IsNullOrEmpty(subType))
            return [];

        var uris = subType switch
        {
            "PrefabModel" => QueryScalars(connection, """
                SELECT file_path AS uri
                FROM prefab_elements
                WHERE prefab_model_id=@id
                  AND state_id=(
                      SELECT MIN(state_id)
                      FROM prefab_elements
                      WHERE prefab_model_id=@id AND state_id>0
                  )
                ORDER BY file_path
                """, subId),
            "ShipModel" => QueryScalars(connection, "SELECT normal AS uri FROM ship_models WHERE id=@id", subId),
            "VehicleModel" => QueryScalars(connection, "SELECT normal AS uri FROM vehicle_models WHERE id=@id", subId),
            // ActorModel is a character rig; its attach points are bones in a .chr, not helpers in a .cgf.
            _ => []
        };

        var result = new List<(string Mesh, Matrix4x4 Transform)>();
        foreach (var uri in uris.Where(uri => !string.IsNullOrWhiteSpace(uri)).Distinct(StringComparer.OrdinalIgnoreCase))
            result.AddRange(ResolvePrefabUri(uri));
        return result;
    }

    private static List<string> QueryScalars(SqliteConnection connection, string sql, uint id)
    {
        var result = new List<string>();
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        command.Parameters.AddWithValue("@id", id);
        command.Prepare();
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
            result.Add(reader.GetString("uri", string.Empty));
        return result;
    }

    /// <summary>
    /// "prefab://prefabs/housing_farm.xml/housing_farm.step1" → the cgf its Brush references.
    /// A cgf path may also be given directly as "cgf://objects/…".
    /// </summary>
    private List<(string Mesh, Matrix4x4 Transform)> ResolvePrefabUri(string uri)
    {
        var scheme = uri.IndexOf("://", StringComparison.Ordinal);
        if (scheme < 0)
            return [];

        var kind = uri[..scheme];
        var rest = uri[(scheme + 3)..].Replace('\\', '/');

        if (kind.StartsWith("cgf", StringComparison.OrdinalIgnoreCase) ||
            kind.StartsWith("cga", StringComparison.OrdinalIgnoreCase))
            return [(ToClientPath(rest), Matrix4x4.Identity)];

        if (!kind.Equals("prefab", StringComparison.OrdinalIgnoreCase))
            return [];

        var xmlEnd = rest.IndexOf(".xml/", StringComparison.OrdinalIgnoreCase);
        if (xmlEnd < 0)
            return [];

        var libraryPath = ToClientPath(rest[..(xmlEnd + 4)]);
        var prefabName = rest[(xmlEnd + 5)..];

        var meshes = GetPrefabMeshes(libraryPath);
        return meshes.TryGetValue(prefabName, out var brushes) ? brushes : [];
    }

    private static string ToClientPath(string relative)
    {
        relative = relative.Replace('\\', '/').TrimStart('/').ToLowerInvariant();
        return relative.StartsWith("game/", StringComparison.Ordinal) ? relative : "game/" + relative;
    }

    /// <summary>Prefab name → every brush it places, parsed once per library.</summary>
    private Dictionary<string, List<(string Mesh, Matrix4x4 Transform)>> GetPrefabMeshes(string libraryPath)
    {
        if (_prefabMeshCache.TryGetValue(libraryPath, out var cached))
            return cached;

        var result = new Dictionary<string, List<(string, Matrix4x4)>>(StringComparer.OrdinalIgnoreCase);
        _prefabMeshCache[libraryPath] = result;

        var xml = ClientFileManager.GetFileAsString(libraryPath);
        if (string.IsNullOrWhiteSpace(xml))
        {
            Logger.Trace($"prefab library not found: {libraryPath}");
            return result;
        }

        try
        {
            var doc = XDocument.Parse(xml);
            var prefabs = doc.Descendants("Prefab")
                .Where(prefab => !string.IsNullOrWhiteSpace((string)prefab.Attribute("Name")))
                .GroupBy(prefab => (string)prefab.Attribute("Name"), StringComparer.OrdinalIgnoreCase)
                .ToDictionary(group => group.Key, group => group.First(), StringComparer.OrdinalIgnoreCase);
            var resolving = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            List<(string Mesh, Matrix4x4 Transform)> ResolveLocal(string name)
            {
                if (result.TryGetValue(name, out var resolved))
                    return resolved;
                if (!prefabs.TryGetValue(name, out var prefab) || !resolving.Add(name))
                    return [];

                var brushes = new List<(string Mesh, Matrix4x4 Transform)>();

                void Collect(XElement container, Matrix4x4 parentTransform)
                {
                    foreach (var obj in container.Elements("Object"))
                    {
                        var objectTransform = ParseObjectTransform(obj) * parentTransform;
                        var type = (string)obj.Attribute("Type");
                        var reference = (string)obj.Attribute("Prefab");

                        if (string.Equals(type, "Brush", StringComparison.OrdinalIgnoreCase) &&
                            !string.IsNullOrWhiteSpace(reference))
                        {
                            brushes.Add((ToClientPath(reference), objectTransform));
                        }
                        else if (string.Equals(type, "Prefab", StringComparison.OrdinalIgnoreCase) &&
                                 !string.IsNullOrWhiteSpace(reference))
                        {
                            var nested = reference.Contains("://", StringComparison.Ordinal)
                                ? ResolvePrefabUri(reference)
                                : ResolveLocal(reference);
                            foreach (var (mesh, transform) in nested)
                                brushes.Add((mesh, transform * objectTransform));
                        }

                        var children = obj.Element("Objects");
                        if (children != null)
                            Collect(children, objectTransform);
                    }
                }

                var objects = prefab.Element("Objects");
                if (objects != null)
                    Collect(objects, Matrix4x4.Identity);
                resolving.Remove(name);
                result[name] = brushes;
                return brushes;
            }

            foreach (var name in prefabs.Keys.Order(StringComparer.Ordinal))
                ResolveLocal(name);
        }
        catch (Exception ex)
        {
            Logger.Warn($"Could not parse prefab library {libraryPath}: {ex.Message}");
        }

        return result;
    }

    private static Matrix4x4 ParseObjectTransform(XElement element)
    {
        var position = ParseVector((string)element.Attribute("Pos"), Vector3.Zero);
        var scale = ParseVector((string)element.Attribute("Scale"), Vector3.One);
        var rotation = ParseQuaternion((string)element.Attribute("Rotate"));
        return Matrix4x4.CreateScale(scale) *
               Matrix4x4.CreateFromQuaternion(rotation) *
               Matrix4x4.CreateTranslation(position);
    }

    private static Vector3 ParseVector(string value, Vector3 fallback)
    {
        if (string.IsNullOrWhiteSpace(value))
            return fallback;

        var parts = value.Split(',');
        if (parts.Length < 3)
            return fallback;

        return float.TryParse(parts[0], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var x) &&
               float.TryParse(parts[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var y) &&
               float.TryParse(parts[2], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var z)
            ? new Vector3(x, y, z)
            : fallback;
    }

    private static Quaternion ParseQuaternion(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return Quaternion.Identity;

        var parts = value.Split(',');
        if (parts.Length < 4)
            return Quaternion.Identity;

        var style = System.Globalization.NumberStyles.Float;
        var culture = System.Globalization.CultureInfo.InvariantCulture;
        return float.TryParse(parts[0], style, culture, out var x) &&
               float.TryParse(parts[1], style, culture, out var y) &&
               float.TryParse(parts[2], style, culture, out var z) &&
               float.TryParse(parts[3], style, culture, out var w)
            ? Quaternion.Normalize(new Quaternion(x, y, z, w))
            : Quaternion.Identity;
    }

    private Dictionary<string, CgfHelperTransform> ReadMeshHelpers(string meshPath)
    {
        if (_meshHelperCache.TryGetValue(meshPath, out var cached))
            return cached;

        var helpers = new Dictionary<string, CgfHelperTransform>(StringComparer.OrdinalIgnoreCase);
        _meshHelperCache[meshPath] = helpers;

        using var stream = ClientFileManager.GetFileStream(meshPath);
        if (stream == null)
            return helpers;

        using var ms = new MemoryStream();
        stream.CopyTo(ms);
        foreach (var (name, transform) in CgfHelperReader.ReadHelpers(ms.ToArray(), meshPath))
            helpers[name] = transform;

        return helpers;
    }
}

public sealed class ModelAttachPointCatalogFile
{
    public const int CurrentSchemaVersion = 1;

    public int SchemaVersion { get; set; } = CurrentSchemaVersion;
    public string ClientBuild { get; set; } = "10.0.2.13-r575";
    public Dictionary<uint, Dictionary<AttachPointKind, HousingLocalTransform>> Models { get; set; } = [];
}
