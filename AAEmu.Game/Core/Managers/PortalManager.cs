using System.Numerics;

using System.Globalization;
using System.Text.RegularExpressions;

using AAEmu.Commons.Exceptions;
using AAEmu.Commons.IO;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.IO;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.OpenPortal;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Teleport;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Models.Tasks.World;
using AAEmu.Game.Utils;
using AAEmu.Game.Utils.DB;

using NLog;

using Portal = AAEmu.Game.Models.Game.Portal;

namespace AAEmu.Game.Core.Managers;

public class PortalManager(ILocalizationManager localizationManager, IWorldManager worldManager, IZoneManager zoneManager, ISubZoneManager subZoneManager, INpcManager npcManager, IObjectIdManager objectIdManager, ITaskManager taskManager) : Singleton<PortalManager>, IPortalManager
{
    public PortalManager(ILocalizationManager localizationManager, IWorldManager worldManager,
        IZoneManager zoneManager, INpcManager npcManager, IObjectIdManager objectIdManager,
        ITaskManager taskManager) : this(localizationManager, worldManager, zoneManager, null,
            npcManager, objectIdManager, taskManager) { }

    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    private static readonly Regex NativeReturnPointPathPattern = new(
        @"^game/worlds/(?<world>main_world|instance_phantom_of_delphinad)/level_design/zone/(?<zone>\d+)/world_server/return_point\.g$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);
    private static readonly Regex NativeReturnPointObjectPattern = new(
        @"(?ms)^object\s*\r?\n(?<body>.*?)(?=^object\s*$|\z)",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);
    private static readonly Regex NativeReturnPointNamePattern = new(
        @"^\s*name\s+ReturnPoint_(?<name>\S+)\s*$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase | RegexOptions.Multiline);
    private static readonly Regex NativeReturnPointPositionPattern = new(
        @"^\s*pos\s+\(\s*x\s+(?<x>[-+0-9.eE]+),\s*y\s+(?<y>[-+0-9.eE]+),\s*z\s+(?<z>[-+0-9.eE]+)\s*\)\s*$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase | RegexOptions.Multiline);
    private static readonly Regex NativeReturnPointRotationPattern = new(
        @"^\s*zRot\s+(?<zRot>[-+0-9.eE]+)\s*$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase | RegexOptions.Multiline);

    private Dictionary<uint, List<Portal>> _recalls;
    private Dictionary<uint, uint> _recallsKey;
    private readonly Dictionary<uint, List<Portal>> _districtRecalls = [];
    private readonly Dictionary<uint, Portal> _nativeRecallsById = [];
    private readonly Dictionary<uint, Portal> _nativeReturnDestinationsById = [];
    private readonly Dictionary<int, uint> _integrationReturnPoints = [];

    public uint GetIntegrationReturnPoint(int direction) => _integrationReturnPoints.GetValueOrDefault(direction);
    private Dictionary<uint, Portal> _respawns;
    private Dictionary<uint, uint> _respawnsKey;
    private Dictionary<uint, Portal> _worldGates;
    private Dictionary<uint, uint> _worldGatesKey;
    private Dictionary<uint, Portal> _levelReturns;

    private Dictionary<uint, OpenPortalReagents> _openPortalInlandReagents;
    private Dictionary<uint, OpenPortalReagents> _openPortalOutlandReagents;
    private Dictionary<uint, DistrictReturnPoints> _districtReturnPoints;
    private readonly Dictionary<uint, HashSet<Models.Game.Units.Portal>> _ownerPortals = [];
    private readonly Lock _ownerPortalsLock = new();

    internal readonly record struct NativeReturnPoint(
        uint ZoneId,
        string EditorName,
        float X,
        float Y,
        float Z,
        float ZRotRadians);

    public List<Portal> GetRecallBySubZoneId(uint subZoneId)
    {
        return _recalls != null && _recalls.TryGetValue(subZoneId, out var recall)
            ? recall
            : null;
    }

    public Portal GetRecallById(uint returnPointId)
    {
        if (_recallsKey == null || !_recallsKey.TryGetValue(returnPointId, out var key))
            return _nativeRecallsById.GetValueOrDefault(returnPointId);
        if (!_recalls.TryGetValue(key, out var portals)) { return null; }

        return portals.FirstOrDefault(portal => portal.Id == returnPointId);
    }

    public List<Portal> GetRecallByDistrictId(uint districtId) => _districtRecalls.GetValueOrDefault(districtId);

    public List<Portal> GetRecallByVisitKey(uint visitKey)
    {
        if (PortalVisitKey.IsDistrict(visitKey))
            return GetRecallByDistrictId(PortalVisitKey.DistrictId(visitKey));
        if (PortalVisitKey.IsSubZone(visitKey))
            return GetRecallBySubZoneId(PortalVisitKey.SubZoneId(visitKey));

        // Prior builds mixed district aliases into the subzone dictionary. Preserve already
        // saved books, but never interpret a new Zone event through that ambiguous namespace.
        return (GetRecallBySubZoneId(visitKey) ?? [])
            .Concat(GetRecallByDistrictId(visitKey) ?? []).DistinctBy(portal => portal.Id).ToList();
    }

    public Portal GetRespawnBySubZoneId(uint subZoneId)
    {
        return _respawns != null && _respawns.TryGetValue(subZoneId, out var respawn)
            ? respawn
            : null;
    }

    public Portal GetRespawnById(uint id)
    {
        return _respawnsKey != null && _respawnsKey.TryGetValue(id, out var key)
            ? _respawns.GetValueOrDefault(key)
            : null;
    }

    public Portal GetWorldGatesBySubZoneId(uint subZoneId)
    {
        return _worldGates != null && _worldGates.TryGetValue(subZoneId, out var worldGate)
            ? worldGate
            : null;
    }

    public Portal GetWorldGatesById(uint id)
    {
        return _worldGatesKey != null && _worldGatesKey.TryGetValue(id, out var key)
            ? _worldGates.GetValueOrDefault(key)
            : null;
    }

    /// <summary>
    /// Resolves an explicit Return special-effect destination. Quest and travel skills share the
    /// same Return effect, but its value can reference either a worldgate or a normal return point.
    /// Keep worldgates authoritative on the few overlapping ids and fall back to the recall
    /// catalogue when no worldgate exists.
    /// </summary>
    public Portal GetReturnDestinationById(uint id)
    {
        return GetWorldGatesById(id) ?? GetRecallById(id) ?? _nativeReturnDestinationsById.GetValueOrDefault(id);
    }

    public Portal GetReturnPoint(uint id) => GetReturnDestinationById(id);

    private Portal GetCommunityReturnPoint(uint returnPointId)
    {
        var gate = GetWorldGatesById(returnPointId);
        if (gate != null)
            return gate;
        var recall = GetRecallById(returnPointId);
        if (recall != null)
            return recall;
        return _levelReturns != null && _levelReturns.TryGetValue(returnPointId, out var level)
            ? level
            : null;
    }

    /// <summary>
    /// Destinations loaded from <c>return_point.g</c> through compact <c>editor_name</c>.
    /// Memory Tome / worldgate JSON is a different id space and is not included.
    /// Empty when <c>ZoneGameDataRoot</c> is unset.
    /// </summary>
    public IReadOnlyList<Portal> GetLevelReturnPoints()
    {
        if (_levelReturns == null || _levelReturns.Count == 0)
            return [];
        return [.. _levelReturns.Values];
    }

    /// <summary>
    /// GetDistrictReturnPoint - вернуть точку возврата для соответствующего DistrictId
    /// </summary>
    /// <param name="districtId"></param>
    /// <returns>ReturnPointId</returns>
    public uint GetDistrictReturnPoint(uint districtId)
    {
        return (
            from point in _districtReturnPoints
            where point.Value.DistrictId == districtId
            select point.Value.ReturnPointId).FirstOrDefault();
    }

    /// <summary>
    /// GetDistrictReturnPoint - вернуть точку возврата для соответствующего DistrictId и FactionId, так как точки для фракций могут быть разные
    /// </summary>
    /// <param name="districtId"></param>
    /// <param name="factionId"></param>
    /// <returns>ReturnPointId</returns>
    public uint GetDistrictReturnPoint(uint districtId, FactionsEnum factionId)
    {
        return (
            from point in _districtReturnPoints
            where point.Value.DistrictId == districtId
            where point.Value.FactionId == factionId
            select point.Value.ReturnPointId).FirstOrDefault();
    }

    /// <summary>
    /// Inverse of <see cref="GetDistrictReturnPoint"/> — the portal-book wire <c>id</c> is the
    /// district, while <c>type</c> carries the return-point id (live SC 0x089 capture).
    /// </summary>
    public uint GetDistrictIdByReturnPoint(uint returnPointId, FactionsEnum factionId)
    {
        return (
            from point in _districtReturnPoints
            where point.Value.ReturnPointId == returnPointId
            where point.Value.FactionId == factionId
            select point.Value.DistrictId).FirstOrDefault();
    }

    public void Load()
    {
        _openPortalInlandReagents = [];
        _openPortalOutlandReagents = [];
        //_allDistrictPortals = new Dictionary<uint, Portal>();
        //_allDistrictPortalsKey = new Dictionary<uint, uint>();
        _districtReturnPoints = [];

        _recalls = [];
        _districtRecalls.Clear();
        _nativeRecallsById.Clear();
        _nativeReturnDestinationsById.Clear();
        _respawns = [];
        _worldGates = [];
        _levelReturns = [];
        _recallsKey = [];
        _respawnsKey = [];
        _worldGatesKey = [];

        Logger.Info("Loading Portals ...");

        #region FileManager

        // Memory Tome destinations: return_point.g + subzone_area.xml + district kind filter,
        // then propagate into child sub_zones (parent_sub_zone_id) so nested-district visits keep working.

        var filePath = Path.Combine(FileManager.AppPath, "Data", "Portal", "respawns.json");
        if (!File.Exists(filePath))
            throw new IOException($"File {filePath} doesn't exists !");

        var contents = FileManager.GetFileContents(filePath);

        if (string.IsNullOrWhiteSpace(contents))
            throw new IOException($"File {filePath} is empty !");

        if (JsonHelper.TryDeserializeObject(contents, out List<Portal> recalls, out _))
            foreach (var recall in recalls)
            {
                recall.Name = localizationManager.Get("return_points", "name", recall.Id, recall.Name);
                RegisterRecall(recall);
            }
        else
            throw new GameException($"PortalManager: Parse {filePath} file");

        Logger.Info($"Loaded {_recalls.Count} Recall Portals");

        filePath = Path.Combine(FileManager.AppPath, "Data", "Portal", "respawns.json");
        if (!File.Exists(filePath))
            throw new IOException($"File {filePath} doesn't exists !");

        contents = FileManager.GetFileContents(filePath);

        if (string.IsNullOrWhiteSpace(contents))
            throw new IOException($"File {filePath} is empty !");

        if (JsonHelper.TryDeserializeObject(contents, out List<Portal> respawns, out _))
            foreach (var respawn in respawns)
            {
                respawn.ZoneId = worldManager.GetZoneId(worldManager.GetWorldTemplateByName("main_world"), respawn.X, respawn.Y);
                if (_respawns.ContainsKey(respawn.SubZoneId))
                {
                    //
                }
                _respawns.Add(respawn.SubZoneId, respawn);
                _respawnsKey.Add(respawn.Id, respawn.SubZoneId);
            }
        else
            throw new GameException($"PortalManager: Parse {filePath} file");

        Logger.Info($"Loaded {_respawns.Count} Respawn Portals");

        filePath = Path.Combine(FileManager.AppPath, "Data", "Portal", "worldgates.json");
        if (!File.Exists(filePath))
            throw new IOException($"File {filePath} doesn't exists !");

        contents = FileManager.GetFileContents(filePath);

        if (string.IsNullOrWhiteSpace(contents))
            throw new IOException($"File {filePath} is empty !");

        if (JsonHelper.TryDeserializeObject(contents, out List<Portal> worldGates, out _))
            foreach (var worldGate in worldGates)
            {
                _worldGates.Add(worldGate.SubZoneId, worldGate);
                _worldGatesKey.Add(worldGate.Id, worldGate.SubZoneId);
            }
        else
            throw new GameException($"PortalManager: Parse {filePath} file");

        Logger.Info($"Loaded {_worldGates.Count} Worldgate Portals");

        #endregion

        #region Sqlite

        var nativeBookReturnPoints = new Dictionary<string, uint>(StringComparer.OrdinalIgnoreCase);
        var nativeReturnPoints = new Dictionary<string, uint>(StringComparer.OrdinalIgnoreCase);
        var bindingDistrictsByReturnPoint = new Dictionary<uint, HashSet<uint>>();
        using (var connection = SQLite.CreateConnection())
        {
            _integrationReturnPoints.Clear();
            using (var command = connection.CreateCommand())
            {
                command.CommandText = """
                    SELECT 0 AS direction, return_point_id AS id FROM const_return_points WHERE name='gatekeeper_hall'
                    UNION ALL
                    SELECT 1 AS direction, id FROM return_points WHERE editor_name='navel_of_the_world'
                    """;
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                    _integrationReturnPoints.Add(reader.GetInt32("direction"), reader.GetUInt32("id"));
            }
            // Return effects also reference quest destinations that have no Memory Tome binding.
            // Only unambiguous editor names can be joined to authored return_point.g objects.
            using (var command = connection.CreateCommand())
            {
                command.CommandText = """
                    SELECT MIN(id) AS id, editor_name FROM return_points
                    WHERE editor_name IS NOT NULL AND editor_name <> ''
                    GROUP BY editor_name COLLATE NOCASE HAVING COUNT(*) = 1
                    """;
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                    nativeReturnPoints.Add((string)reader.GetValue("editor_name"), reader.GetUInt32("id"));
            }
            // NOTE - priority -> to remove item from inventory first
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM open_portal_inland_reagents";
                command.Prepare();
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                {
                    var template = new OpenPortalReagents
                    {
                        Id = reader.GetUInt32("id"),
                        OpenPortalEffectId = reader.GetUInt32("open_portal_effect_id"),
                        ItemId = reader.GetUInt32("item_id"),
                        Amount = reader.GetInt32("amount"),
                        Priority = reader.GetInt32("priority")
                    };
                    _openPortalInlandReagents.Add(template.Id, template);
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM open_portal_outland_reagents";
                command.Prepare();
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                {
                    var template = new OpenPortalReagents
                    {
                        Id = reader.GetUInt32("id"),
                        OpenPortalEffectId = reader.GetUInt32("open_portal_effect_id"),
                        ItemId = reader.GetUInt32("item_id"),
                        Amount = reader.GetInt32("amount"),
                        Priority = reader.GetInt32("priority")
                    };
                    _openPortalOutlandReagents.Add(template.Id, template);
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM district_return_points";
                command.Prepare();
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                {
                    var template = new DistrictReturnPoints
                    {
                        Id = reader.GetUInt32("id"),
                        DistrictId = reader.GetUInt32("district_id"),
                        FactionId = (FactionsEnum)reader.GetUInt32("faction_id"),
                        ReturnPointId = reader.GetUInt32("return_point_id")
                    };
                    _districtReturnPoints.TryAdd(template.Id, template);
                }
            }

            // The teleport book is defined by Memory Tome binding districts. The old JSON only
            // covered a small hand-maintained subset; r575 carries the complete relation in SQLite.
            using (var command = connection.CreateCommand())
            {
                command.CommandText = """
                    WITH book_bindings AS (
                        SELECT DISTINCT binding.district_id, groups.doodad_almighty_id
                        FROM doodad_funcs func
                        JOIN doodad_func_groups groups ON groups.id = func.doodad_func_group_id
                        JOIN doodad_func_bindings binding ON binding.id = func.actual_func_id
                        WHERE func.actual_func_type = 'DoodadFuncBinding'
                          AND COALESCE(binding.zone_id, 0) = 0
                    )
                    SELECT DISTINCT point.id, point.editor_name, book.district_id
                    FROM return_points point
                    JOIN district_return_points district ON district.return_point_id = point.id
                    JOIN book_bindings book ON book.district_id = district.district_id
                    WHERE point.editor_name IS NOT NULL AND point.editor_name <> ''
                    ORDER BY point.id, book.doodad_almighty_id
                    """;
                command.Prepare();
                using var reader = new SQLiteWrapperReader(command.ExecuteReader());
                while (reader.Read())
                {
                    var id = reader.GetUInt32("id");
                    var editorName = (string)reader.GetValue("editor_name");
                    if (nativeBookReturnPoints.TryGetValue(editorName, out var existingId))
                    {
                        if (existingId != id)
                            Logger.Warn($"Duplicate native return-point editor name '{editorName}' (ids {existingId}/{id})");
                    }
                    else
                    {
                        nativeBookReturnPoints.Add(editorName, id);
                    }

                    if (!bindingDistrictsByReturnPoint.TryGetValue(id, out var districtIds))
                    {
                        districtIds = [];
                        bindingDistrictsByReturnPoint.Add(id, districtIds);
                    }
                    districtIds.Add(reader.GetUInt32("district_id"));
                }
            }
        }

        LoadNativeRecallCatalogue(nativeBookReturnPoints, bindingDistrictsByReturnPoint, nativeReturnPoints);
        Logger.Info("Loaded Portal Info");
        #endregion
    }

    private void RegisterRecall(Portal recall)
    {
        if (!_recalls.TryGetValue(recall.SubZoneId, out var portals))
        {
            portals = [];
            _recalls.Add(recall.SubZoneId, portals);
        }

        if (portals.All(existing => existing.Id != recall.Id))
            portals.Add(recall);

        _recallsKey.TryAdd(recall.Id, recall.SubZoneId);
    }

    private void LoadNativeRecallCatalogue(
        IReadOnlyDictionary<string, uint> nativeBookReturnPoints,
        IReadOnlyDictionary<uint, HashSet<uint>> bindingDistrictsByReturnPoint,
        IReadOnlyDictionary<string, uint> nativeReturnPoints)
    {
        var files = ClientFileManager.GetFilesInDirectory(
            Path.Combine("game", "worlds", "main_world", "level_design", "zone"),
            "return_point.g",
            true).Concat(ClientFileManager.GetFilesInDirectory(
                Path.Combine("game", "worlds", "instance_phantom_of_delphinad", "level_design", "zone"),
                "return_point.g", true));
        var matchedReturnPointIds = new HashSet<uint>();
        var nativePortalsById = new Dictionary<uint, Portal>();
        var registeredAliases = 0;
        var authoredPoints = new List<NativeReturnPoint>();

        foreach (var fileName in files)
        {
            var normalizedPath = fileName.Replace('\\', '/');
            var pathMatch = NativeReturnPointPathPattern.Match(normalizedPath);
            if (!pathMatch.Success ||
                !uint.TryParse(pathMatch.Groups["zone"].Value, NumberStyles.None,
                    CultureInfo.InvariantCulture, out var zoneId))
                continue;

            var contents = ClientFileManager.GetFileAsString(fileName);
            if (string.IsNullOrWhiteSpace(contents))
                continue;

            foreach (var nativePoint in ParseNativeReturnPoints(zoneId, contents))
            {
                authoredPoints.Add(nativePoint);
                // Instance quest portals are explicit destinations, not teleport-book unlocks.
                if (pathMatch.Groups["world"].Value != "main_world")
                    continue;
                if (!nativeBookReturnPoints.TryGetValue(nativePoint.EditorName, out var returnPointId))
                    continue;

                matchedReturnPointIds.Add(returnPointId);
                var position = zoneManager.ConvertToWorldCoordinates(zoneId,
                    new Vector3(nativePoint.X, nativePoint.Y, nativePoint.Z));
                var portal = GetRecallById(returnPointId) ?? new Portal
                {
                    Id = returnPointId,
                    Name = localizationManager.Get("return_points", "name", returnPointId, nativePoint.EditorName),
                    ZoneId = zoneId,
                    X = position.X,
                    Y = position.Y,
                    Z = position.Z,
                    ZRot = nativePoint.ZRotRadians * 180f / MathF.PI
                };
                nativePortalsById.TryAdd(returnPointId, portal);
                _nativeRecallsById.TryAdd(returnPointId, portal);

                var worldTemplate = worldManager.GetWorldTemplateByZoneKey(zoneId);
                if (worldTemplate == null)
                {
                    Logger.Warn($"No world template for native return point {returnPointId} in zone {zoneId}");
                    continue;
                }

                var subZones = subZoneManager.GetSubZoneByPosition(worldTemplate, position)
                    .Distinct()
                    .ToArray();
                if (subZones.Length == 0)
                {
                    Logger.Debug($"Native return point {returnPointId} ({nativePoint.EditorName}) uses " +
                                 "district-area discovery; destination has no client subzone");
                    continue;
                }

                foreach (var subZoneId in subZones)
                {
                    RegisterRecall(new Portal
                    {
                        Id = portal.Id,
                        Name = portal.Name,
                        Type = portal.Type,
                        ZoneId = portal.ZoneId,
                        X = portal.X,
                        Y = portal.Y,
                        Z = portal.Z,
                        ZRot = portal.ZRot,
                        Yaw = portal.Yaw,
                        SubZoneId = subZoneId,
                        WorldId = portal.WorldId
                    });
                    registeredAliases++;
                }
            }
        }

        foreach (var (id, destination) in BuildNativeReturnDestinations(authoredPoints, nativeReturnPoints,
                     zoneId => worldManager.GetWorldTemplateByZoneKey(zoneId) != null
                         ? zoneManager.GetZoneOriginCell(zoneId) : null))
        {
            _nativeReturnDestinationsById.Add(id, destination);
            if (worldManager.GetWorldTemplateByZoneKey(destination.ZoneId)?.Name == "instance_phantom_of_delphinad")
                Logger.Info("Native instance Return destination: point={0}, zone={1}, xyz=({2},{3},{4})",
                    id, destination.ZoneId, destination.X, destination.Y, destination.Z);
        }
        Logger.Info("Native r575 explicit Return catalogue: {0} destinations (independent of teleport-book discovery)",
            _nativeReturnDestinationsById.Count);

        // The client explicitly binds every Memory Tome to a district. That relation is the
        // authoritative unlock trigger even when the return destination lies outside the
        // district polygon or the tome itself is spawned dynamically. Do not infer the district
        // from distance to either object.
        var bindingAliases = RegisterBindingDistrictAliases(
            nativePortalsById,
            bindingDistrictsByReturnPoint);

        var availableReturnPointIds = nativeBookReturnPoints.Values
            .Distinct()
            .Count(returnPointId => GetRecallById(returnPointId) != null);
        var missingReturnPointIds = nativeBookReturnPoints.Values
            .Distinct()
            .Where(returnPointId => GetRecallById(returnPointId) == null)
            .Order()
            .ToArray();

        Logger.Info($"Native r575 teleport-book catalogue: {availableReturnPointIds}/" +
                    $"{nativeBookReturnPoints.Values.Distinct().Count()} return points available, " +
                    $"{matchedReturnPointIds.Count} matched in return_point.g, {registeredAliases} destination aliases, " +
                    $"{bindingAliases} binding-district aliases");
        if (missingReturnPointIds.Length > 0)
            Logger.Warn($"Teleport-book return points without an r575 world placement: " +
                        string.Join(',', missingReturnPointIds));
    }

    internal static Dictionary<uint, Portal> BuildNativeReturnDestinations(
        IEnumerable<NativeReturnPoint> points, IReadOnlyDictionary<string, uint> idsByEditorName,
        Func<uint, Vector2?> getOriginCell)
    {
        var result = new Dictionary<uint, Portal>();
        var conflictingIds = new HashSet<uint>();
        foreach (var point in points.Distinct())
        {
            if (!idsByEditorName.TryGetValue(point.EditorName, out var id) || id == 0 ||
                getOriginCell(point.ZoneId) is not { } origin || conflictingIds.Contains(id))
                continue;
            var position = new Vector3(origin.X * 1024f + point.X, origin.Y * 1024f + point.Y, point.Z);
            if (!float.IsFinite(position.X) || !float.IsFinite(position.Y) || !float.IsFinite(position.Z) ||
                !float.IsFinite(point.ZRotRadians))
                continue;
            var portal = new Portal
            {
                Id = id, Name = point.EditorName, ZoneId = point.ZoneId,
                X = position.X, Y = position.Y, Z = position.Z,
                Yaw = point.ZRotRadians * 180f / MathF.PI,
                ZRot = point.ZRotRadians * 180f / MathF.PI
            };
            if (!result.TryAdd(id, portal))
            {
                // Never select an arbitrary placement when one return id has several destinations.
                result.Remove(id);
                conflictingIds.Add(id);
            }
        }
        return result;
    }

    private int RegisterBindingDistrictAliases(
        IReadOnlyDictionary<uint, Portal> nativePortalsById,
        IReadOnlyDictionary<uint, HashSet<uint>> bindingDistrictsByReturnPoint)
    {
        var aliases = 0;
        foreach (var (returnPointId, districtIds) in bindingDistrictsByReturnPoint)
        {
            var portal = GetRecallById(returnPointId);
            if (portal == null && !nativePortalsById.TryGetValue(returnPointId, out portal))
                continue;

            foreach (var districtId in districtIds)
            {
                if (!_districtRecalls.TryGetValue(districtId, out var portals))
                    _districtRecalls.Add(districtId, portals = []);
                if (portals.All(existing => existing.Id != returnPointId))
                {
                    portals.Add(CloneRecallForSubZone(portal, PortalVisitKey.ForDistrict(districtId)));
                    aliases++;
                }
            }
        }

        return aliases;
    }

    private static Portal CloneRecallForSubZone(Portal portal, uint subZoneId) => new()
    {
        Id = portal.Id,
        Name = portal.Name,
        Type = portal.Type,
        ZoneId = portal.ZoneId,
        X = portal.X,
        Y = portal.Y,
        Z = portal.Z,
        ZRot = portal.ZRot,
        Yaw = portal.Yaw,
        SubZoneId = subZoneId,
        WorldId = portal.WorldId
    };

    internal static IReadOnlyList<NativeReturnPoint> ParseNativeReturnPoints(uint zoneId, string contents)
    {
        var result = new List<NativeReturnPoint>();
        foreach (Match objectMatch in NativeReturnPointObjectPattern.Matches(contents))
        {
            var body = objectMatch.Groups["body"].Value;
            var nameMatch = NativeReturnPointNamePattern.Match(body);
            var positionMatch = NativeReturnPointPositionPattern.Match(body);
            if (!nameMatch.Success || !positionMatch.Success)
                continue;

            var rotationMatch = NativeReturnPointRotationPattern.Match(body);
            result.Add(new NativeReturnPoint(
                zoneId,
                nameMatch.Groups["name"].Value,
                ParseNativeFloat(positionMatch, "x"),
                ParseNativeFloat(positionMatch, "y"),
                ParseNativeFloat(positionMatch, "z"),
                rotationMatch.Success ? ParseNativeFloat(rotationMatch, "zRot") : 0f));
        }

        return result;
    }

    private static float ParseNativeFloat(Match match, string group) =>
        float.Parse(match.Groups[group].Value, NumberStyles.Float, CultureInfo.InvariantCulture);

    private void LoadLevelReturnPoints(IReadOnlyDictionary<string, uint> editorNameToId)
    {
        var roots = EnumerateZoneGameDataRoots();
        if (roots.Count == 0)
        {
            Logger.Warn(
                "ZoneGameDataRoot is not configured — return_point.g destinations are not loaded");
            return;
        }

        var added = 0;
        foreach (var local in ReturnPointGCatalog.LoadFromRoots(roots))
        {
            if (!ReturnPointFileRules.TryGetReturnPointId(editorNameToId, local.EditorName, out var id))
                continue;
            var haveGate = _worldGatesKey.ContainsKey(id);
            var haveRecall = _recallsKey.ContainsKey(id);
            if (!ReturnPointFileRules.ShouldUseLevelFile(haveGate, haveRecall))
                continue;
            var worldTemplate = worldManager.GetWorldTemplateByZoneKey(local.ZoneKey);
            if (worldTemplate?.XmlWorldZones == null || !worldTemplate.XmlWorldZones.ContainsKey(local.ZoneKey))
            {
                Logger.Warn("return_point.g {0} zone {1} is not loaded", local.EditorName, local.ZoneKey);
                continue;
            }

            var world = zoneManager.ConvertToWorldCoordinates(
                local.ZoneKey,
                new Vector3(local.X, local.Y, local.Z));
            var portal = new Portal
            {
                Id = id,
                Type = id,
                Name = localizationManager.Get("return_points", "name", id, local.EditorName),
                ZoneId = local.ZoneKey,
                X = world.X,
                Y = world.Y,
                Z = world.Z,
                ZRot = local.ZRotRadians,
                Yaw = ReturnPointFileRules.YawDegreesFromZRot(local.ZRotRadians)
            };
            if (_levelReturns.TryAdd(id, portal))
                added++;
        }

        Logger.Info("Loaded {0} return_point.g destinations", added);
    }

    private static List<string> EnumerateZoneGameDataRoots() => ZoneGameDataRoots.Enumerate();

    public static bool CheckItemAndRemove(Character owner, uint itemId, int amount)
    {
        if (!owner.Inventory.CheckItems(SlotType.Inventory, itemId, amount)) return false;
        owner.Inventory.Bag.ConsumeItem(ItemTaskType.Teleport, itemId, amount, null);
        return true;
    }

    protected virtual bool CheckCanOpenPortal(Character owner, uint targetZoneId, uint openPortalEffectId)
    {
        var targetContinent = zoneManager.GetTargetIdByZoneId(targetZoneId);
        var ownerContinent = zoneManager.GetTargetIdByZoneId(owner.Transform.ZoneId);
        var source = targetContinent == ownerContinent ? _openPortalInlandReagents : _openPortalOutlandReagents;
        if (source == null)
        {
            Logger.Error("OpenPortal reagent tables are not loaded");
            return false;
        }

        var reagents = OpenPortalReagentRules.ForEffect(source.Values, openPortalEffectId);

        if (reagents.Count == 0)
        {
            Logger.Error("OpenPortal effect {0} has no {1} reagent rows", openPortalEffectId,
                targetContinent == ownerContinent ? "inland" : "outland");
            return false;
        }

        foreach (var reagent in reagents)
        {
            if (CheckItemAndRemove(owner, reagent.ItemId, reagent.Amount))
                return true;
        }
        return false;
    }

    protected void RegisterLivePortal(Character owner, Models.Game.Units.Portal portal)
    {
        lock (_ownerPortalsLock)
        {
            if (!_ownerPortals.TryGetValue(owner.Id, out var portals))
            {
                portals = [];
                _ownerPortals[owner.Id] = portals;
            }
            portals.Add(portal);
        }
    }

    protected virtual void DeleteLivePortal(Models.Game.Units.Portal portal) => portal.Delete();

    /// <summary>Deletes what is still live: a pair member the cascade already removed is skipped.</summary>
    private static void DeleteAlive(IEnumerable<Models.Game.Units.Portal> portals, Action<Models.Game.Units.Portal> delete)
    {
        foreach (var portal in portals)
        {
            // Portal.Delete cascades to the linked portal; without this guard the second member of the
            // pair is deleted again and is sent a second death packet.
            if (!portal.IsDeadOrDeleted)
                delete(portal);
        }
    }

    public void DeleteOwnerPortals(Character owner)
    {
        Models.Game.Units.Portal[] owned;
        lock (_ownerPortalsLock)
        {
            if (owner == null || !_ownerPortals.TryGetValue(owner.Id, out var portals))
                return;

            owned = [.. portals];
            _ownerPortals.Remove(owner.Id);
        }

        DeleteAlive(owned, DeleteLivePortal);
    }

    private void DeleteOwnerPortals(Character owner, Portal sourcePortal)
    {
        Models.Game.Units.Portal[] matched;
        lock (_ownerPortalsLock)
        {
            if (owner == null || sourcePortal == null || !_ownerPortals.TryGetValue(owner.Id, out var portals))
                return;

            matched = [.. portals.Where(portal => ReferenceEquals(portal.SourcePortal, sourcePortal))];
            foreach (var portal in matched)
                portals.Remove(portal);
            if (portals.Count == 0)
                _ownerPortals.Remove(owner.Id);
        }

        DeleteAlive(matched, DeleteLivePortal);
    }

    /// <summary>
    /// Create a portal Npc object and returns it.
    /// </summary>
    protected virtual Models.Game.Units.Portal MakePortal(Character owner, bool isExit, Portal portalInfo,
        SkillObjectUnk1 portalEffectObj, uint templateId)
    {
        var template = npcManager.GetTemplate(templateId);
        if (template == null)
        {
            Logger.Error("OpenPortal NPC template {0} is not loaded", templateId);
            return null;
        }

        var portalPointDestination = new Transform(null, null,
            portalInfo.ZoneId,
            owner.Transform.InstanceId,
            portalInfo.X, portalInfo.Y, portalInfo.Z,
            0f, 0f, portalInfo.ZRot);

        // Enter stays in the caster's zone (book cast position); exit uses the destination zone.
        var liveZoneId = isExit ? portalInfo.ZoneId : owner.Transform.ZoneId;
        var portalNpc = new Models.Game.Units.Portal
        {
            ParentWorld = owner.ParentWorld,
            ObjId = objectIdManager.GetNextId(),
            OwnerId = owner.Id,
            TemplateId = templateId,
            Template = template,
            ModelId = template.ModelId,
            Faction = owner.Faction,
            Level = template.Level,
            Name = portalInfo.Name,
            TeleportPosition = portalPointDestination,
            IsExit = isExit,
            SourcePortal = portalInfo,
            Transform = { ZoneId = liveZoneId }
        };

        if (isExit)
        {
            portalNpc.Transform.Local.SetPosition(portalInfo.X, portalInfo.Y, portalInfo.Z,
                0f, 0f, portalInfo.ZRot);
        }
        else
        {
            portalNpc.Transform.Local.SetPosition(
                portalEffectObj.X, portalEffectObj.Y, portalEffectObj.Z,
                owner.Transform.World.Rotation.X, owner.Transform.World.Rotation.Y, owner.Transform.World.Rotation.Z);
        }

        portalNpc.InitializeSpawnBuffs();
        portalNpc.UpdateGearBonuses(null, null);

        portalNpc.Hp = portalNpc.MaxHp;
        portalNpc.Mp = portalNpc.MaxMp;

        portalNpc.Spawn();
        return portalNpc;
    }

    public void OpenPortal(Character owner, SkillObjectUnk1 portalEffectObj, OpenPortalEffect effect)
    {
        if (owner == null || portalEffectObj == null || effect == null)
            return;

        if (!OpenPortalNpcRules.TryResolve(effect, out var enterNpcId, out var exitNpcId))
        {
            Logger.Error("OpenPortal effect {0} is missing an enter/exit NPC template", effect.Id);
            return;
        }

        if (npcManager.GetTemplate(enterNpcId) == null || npcManager.GetTemplate(exitNpcId) == null)
        {
            Logger.Error("OpenPortal effect {0} references an NPC template that is not loaded", effect.Id);
            return;
        }

        if (portalEffectObj.Id < 0)
        {
            Logger.Warn("OpenPortal effect {0} received a negative portal id", effect.Id);
            return;
        }

        // The cast names the book in portalEffectObj.Type, so resolve through the typed lookup:
        // a private entry that collides with a visited district id must not open the district one.
        var portalInfo = owner.Portals.GetPortalInfoByType((uint)portalEffectObj.Id, portalEffectObj.Type);
        if (portalInfo == null)
        {
            Logger.Warn("OpenPortal effect {0} cannot resolve portal id {1}", effect.Id, portalEffectObj.Id);
            return;
        }

        if (!CheckCanOpenPortal(owner, portalInfo.ZoneId, effect.Id))
            return;

        var entrance = MakePortal(owner, false, portalInfo, portalEffectObj, enterNpcId);
        if (entrance == null)
            return;

        var exit = MakePortal(owner, true, portalInfo, portalEffectObj, exitNpcId);
        if (exit == null)
        {
            entrance.Delete();
            return;
        }

        entrance.LinkedPortal = exit;
        exit.LinkedPortal = entrance;

        // A previous pair for the same book entry is now redundant: the new one serves the same
        // destination. Removing it bounds a live portal set to one pair per book entry.
        DeleteOwnerPortals(owner, portalInfo);

        RegisterLivePortal(owner, entrance);
        RegisterLivePortal(owner, exit);

        // open_portal_effects has no lifetime column. Duration is pinned from the OpenPortal
        // skill description: 30 s, or 60 s when Death (Occultism) ability is level 20+.
        SchedulePortalExpiry(owner, entrance);
    }

    /// <summary>
    /// Arms the worldgate kill timer on the entrance; deleting it cascades to the linked exit.
    /// </summary>
    protected virtual void SchedulePortalExpiry(Character owner, Models.Game.Units.Portal entrance)
    {
        var deathLevel = owner.Abilities?.GetAbilityLevel(PortalOpenDurationRules.ExtendedAbility) ?? 0;
        var lifetime = PortalOpenDurationRules.DurationFor(deathLevel);
        taskManager.Schedule(new KillPortalTask(entrance), lifetime);
    }

    /// <summary>
    /// Walks the character through the portal unit it named. The object id arrives from the client, so
    /// it resolves any open portal in the world and the character has to be one that can reach it.
    /// </summary>
    public void UsePortal(Character character, uint objId, bool onlyMyPortal = false)
    {
        // No cooldown is applied here: no authoritative content/protocol value has been identified.
        if (character.ParentWorld.GetNpc(objId) is not Models.Game.Units.Portal portal) return;

        // The client only sends the use for a portal it collided with, so a portal outside the
        // character's neighbourhood is a forged id and is refused. Portals outlive a single cast, so
        // without this a crafted use teleports the sender to any open pair's destination.
        var portalPosition = portal.Transform.World.Position;
        if (!PortalUseRules.IsReachableFrom(character, portalPosition))
        {
            Logger.Warn("UsePortal: character {0} refused portal {1} at ({2:0.0}, {3:0.0}, {4:0.0}) because it is outside the character's neighbourhood",
                character.Name, portal.ObjId, portalPosition.X, portalPosition.Y, portalPosition.Z);
            return;
        }

        // The client's onlyMyPortal flag asks the server to restrict the use to the owner's own
        // portal. Portals now outlive a single cast, so without this a stale pair stays usable by
        // anyone who walks into it. A portal with no book entry (a GM-created one) has no owner
        // to compare against, so the flag is not enforceable for it.
        var portalOwnerId = portal.SourcePortal?.Owner;
        if (onlyMyPortal && portalOwnerId != character.Id)
        {
            Logger.Warn("UsePortal: character {0} refused portal {1} owned by {2} because onlyMyPortal was set",
                character.Id, portal.ObjId, portalOwnerId ?? 0);
            return;
        }

        //have Overburdened buff cannot UsePortal
        if (character.Buffs.CheckBuffTag((uint)BuffConstants.TagOverburdened))
        {
            character.SendErrorMessage(ErrorMessageType.CannotUsePortalWithBackpack);
            return;
        }

        ApplyPortalUse(character, portal);
    }

    /// <summary>
    /// Confirms the use to the client and lands the character at the portal's destination. Split from
    /// the decision so the decision can be exercised without a landing.
    /// </summary>
    protected virtual void ApplyPortalUse(Character character, Models.Game.Units.Portal portal)
    {
        var destination = portal.TeleportPosition;
        var position = destination.World.Position;

        Logger.Info("UsePortal: {0} -> {1} zone {2} ({3:0.0}, {4:0.0}, {5:0.0})",
            character.Name, portal.Name, destination.ZoneId, position.X, position.Y, position.Z);

        character.SendPacket(new SCUnitPortalUsedPacket(portal.ObjId));

        var destWorld = portal.LinkedPortal?.ParentWorld ?? portal.ParentWorld ?? character.ParentWorld;
        if (!SkillTeleportLanding.TryApplyToWorld(
                character,
                destWorld,
                destination.ZoneId,
                position.X,
                position.Y,
                position.Z,
                destination.World.Rotation.Z,
                TeleportReason.Portal))
        {
            Logger.Warn("UsePortal: {0} could not land at portal {1} zone {2}",
                character.Name, portal.Name, destination.ZoneId);
        }
    }

    public void DeletePortal(Character owner, byte type, uint id)
    {
        var isPrivate = type != 1;
        // The wire type says which book the client named. A type-agnostic lookup answers from the
        // district book first, so deleting a private entry would tear down the district entry's live
        // pair and leave the private one standing.
        var portalInfo = isPrivate
            ? owner.Portals.GetPrivatePortalInfo(id)
            : owner.Portals.GetDistrictPortalInfo(id);
        if (portalInfo == null)
            return;

        owner.Portals.RemoveFromBookPortal(portalInfo, isPrivate);
        // Match the book entry, not its id: the two id spaces overlap.
        DeleteOwnerPortals(owner, portalInfo);
    }

    /// <summary>
    /// Gets the closest valid return portal (respawn) location for a given player
    /// </summary>
    /// <param name="character"></param>
    /// <returns></returns>
    public Portal GetClosestReturnPortal(Character character)
    {
        var currentPosition = character.Transform.World.Position;
        var distance = 999999f;
        var portal = new Portal {
            // Fail-safe coordinates
            X = currentPosition.X,
            Y = currentPosition.Y,
            Z = currentPosition.Z,
            ZoneId = character.Transform.ZoneId
        };

        foreach (var (_, value) in _respawns)
        {
            // Check against district specific faction respawns
            var districts = _districtReturnPoints.Values.Where(d => d.ReturnPointId == value.Id).ToList();
            if (districts.Count > 0)
            {
                var factions = districts.Select(d => d.FactionId).Distinct().ToList();
                if (factions.Count > 0 && !factions.Contains(character.Faction.MotherId) && !factions.Contains(character.Faction.Id))
                {
                    continue;
                }
            }

            // Check if it's a closed zone (for non-admins)
            if (character is { AccessLevel: < 100 })
            {
                var zone = zoneManager.GetZoneByKey(value.ZoneId);
                if (zone is null or { Closed: true })
                {
                    continue;
                }
            }

            // Calculate distance to player
            var portalXyz = new Vector3(value.X, value.Y, value.Z);
            var dist = MathUtil.CalculateDistance(currentPosition, portalXyz);
            if (dist >= distance)
            {
                continue;
            }
            distance = dist;
            portal = value;
        }
        return portal;
    }
}
