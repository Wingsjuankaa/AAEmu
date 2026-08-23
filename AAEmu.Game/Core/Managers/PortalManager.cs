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
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    private static readonly Regex NativeReturnPointPathPattern = new(
        @"^game/worlds/main_world/level_design/zone/(?<zone>\d+)/world_server/return_point\.g$",
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
    private Dictionary<uint, Portal> _respawns;
    private Dictionary<uint, uint> _respawnsKey;
    private Dictionary<uint, Portal> _worldGates;
    private Dictionary<uint, uint> _worldGatesKey;

    private Dictionary<uint, OpenPortalReagents> _openPortalInlandReagents;
    private Dictionary<uint, OpenPortalReagents> _openPortalOutlandReagents;
    private Dictionary<uint, DistrictReturnPoints> _districtReturnPoints;

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
        if (_recallsKey == null || !_recallsKey.TryGetValue(returnPointId, out var key)) { return null; }
        if (!_recalls.TryGetValue(key, out var portals)) { return null; }

        return portals.FirstOrDefault(portal => portal.Id == returnPointId);
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
        return GetWorldGatesById(id) ?? GetRecallById(id);
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
        _respawns = [];
        _worldGates = [];
        _recallsKey = [];
        _respawnsKey = [];
        _worldGatesKey = [];

        Logger.Info("Loading Portals ...");

        #region FileManager

        var filePath = Path.Combine(FileManager.AppPath, "Data", "Portal", "recalls.json");
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
        var bindingDistrictsByReturnPoint = new Dictionary<uint, HashSet<uint>>();
        using (var connection = SQLite.CreateConnection())
        {
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

        LoadNativeRecallCatalogue(nativeBookReturnPoints, bindingDistrictsByReturnPoint);
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
        IReadOnlyDictionary<uint, HashSet<uint>> bindingDistrictsByReturnPoint)
    {
        var files = ClientFileManager.GetFilesInDirectory(
            Path.Combine("game", "worlds", "main_world", "level_design", "zone"),
            "return_point.g",
            true);
        var matchedReturnPointIds = new HashSet<uint>();
        var nativePortalsById = new Dictionary<uint, Portal>();
        var registeredAliases = 0;

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
                    Logger.Warn($"Native return point {returnPointId} ({nativePoint.EditorName}) at " +
                                $"{position.X:0.###},{position.Y:0.###},{position.Z:0.###} has no subzone");
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
                var before = GetRecallBySubZoneId(districtId)?.Count(existing => existing.Id == returnPointId) ?? 0;
                RegisterRecall(CloneRecallForSubZone(portal, districtId));
                var after = GetRecallBySubZoneId(districtId)?.Count(existing => existing.Id == returnPointId) ?? 0;
                if (after > before)
                    aliases++;
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

    public static bool CheckItemAndRemove(Character owner, uint itemId, int amount)
    {
        if (!owner.Inventory.CheckItems(SlotType.Inventory, itemId, amount)) return false;
        owner.Inventory.Bag.ConsumeItem(ItemTaskType.Teleport, itemId, amount, null);
        return true;
    }

    private bool CheckCanOpenPortal(Character owner, uint targetZoneId)
    {
        var targetContinent = zoneManager.GetTargetIdByZoneId(targetZoneId);
        var ownerContinent = zoneManager.GetTargetIdByZoneId(owner.Transform.ZoneId);

        if (targetContinent == ownerContinent)
        {
            foreach (var (_, value) in _openPortalInlandReagents)
            {
                if (CheckItemAndRemove(owner, value.ItemId, value.Amount)) return true;
            }
        }
        else
        {
            foreach (var (_, value) in _openPortalOutlandReagents)
            {
                if (CheckItemAndRemove(owner, value.ItemId, value.Amount)) return true;
            }
        }
        return false; // Not enough items
    }

    /// <summary>open_portal_effects id 1: enter_portal_npc_id — the green portal you walk into.</summary>
    private const uint EntrancePortalNpcId = 3891;
    /// <summary>open_portal_effects id 1: exit_portal_npc_id — the yellow portal at the destination.</summary>
    private const uint ExitPortalNpcId = 6629;

    /// <summary>
    /// Create a portal Npc object and returns it
    /// </summary>
    /// <param name="owner"></param>
    /// <param name="isExit"></param>
    /// <param name="portalInfo"></param>
    /// <param name="portalEffectObj"></param>
    /// <returns></returns>
    private Models.Game.Units.Portal MakePortal(Unit owner, bool isExit, Portal portalInfo, SkillObjectUnk1 portalEffectObj)
    {
        var portalPointDestination = new Transform(null, null, 
            portalInfo.ZoneId,
            owner.Transform.InstanceId,
            portalInfo.X, portalInfo.Y, portalInfo.Z,
            0f, 0f, portalInfo.ZRot);

        // TODO: Add support for different types of teleport books
        var templateId = isExit ? ExitPortalNpcId : EntrancePortalNpcId;
        var template = npcManager.GetTemplate(templateId);
        var portalNpc = new Models.Game.Units.Portal
        {
            ParentWorld = owner.ParentWorld,
            ObjId = objectIdManager.GetNextId(),
            OwnerId = ((Character)owner).Id,
            TemplateId = templateId,
            Template = template,
            ModelId = template.ModelId,
            Faction = owner.Faction, // INFO - FactionManager.Instance.GetFaction(template.FactionId)
            Level = template.Level,
            Name = portalInfo.Name,
            TeleportPosition = portalPointDestination,
            IsExit = isExit,
            Transform = { ZoneId = portalInfo.ZoneId }
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

        var killTask = new KillPortalTask(portalNpc);
        taskManager.Schedule(killTask, TimeSpan.FromSeconds(30));
        return portalNpc;
    }

    public void OpenPortal(Character owner, SkillObjectUnk1 portalEffectObj)
    {
        var portalInfo = owner.Portals.GetPortalInfo((uint)portalEffectObj.Id);
        if (!CheckCanOpenPortal(owner, portalInfo.ZoneId)) return;

        var entrance = MakePortal(owner, false, portalInfo, portalEffectObj);   // Entrance (green)
        var exit = MakePortal(owner, true, portalInfo, portalEffectObj);    // Exit (yellow)
        // Linked the 2 portals
        entrance.LinkedPortal = exit;
        exit.LinkedPortal = entrance;
    }

    public static void UsePortal(Character character, uint objId)
    {
        // TODO - Cooldown between portals
        if (character.ParentWorld.GetNpc(objId) is not Models.Game.Units.Portal portal) return;

        //have Overburdened buff cannot UsePortal
        if (character.Buffs.CheckBuffTag((uint)BuffConstants.TagOverburdened))
        {
            character.SendErrorMessage(ErrorMessageType.CannotUsePortalWithBackpack);
            return;
        }

        var destination = portal.TeleportPosition;
        var position = destination.World.Position;
        var yaw = destination.World.Rotation.Z.DegToRad();

        Logger.Info("UsePortal: {0} -> {1} zone {2} ({3:0.0}, {4:0.0}, {5:0.0})",
            character.Name, portal.Name, destination.ZoneId, position.X, position.Y, position.Z);

        character.SendPacket(new SCUnitPortalUsedPacket(portal.ObjId));

        if (destination.InstanceId != character.Transform.InstanceId)
        {
            // Crossing instances means a loading screen, and the client answers it with
            // CSInstanceLoaded — which is the only thing that clears DisabledSetPosition.
            character.DisabledSetPosition = true;
            character.SendPacket(
                new SCLoadInstancePacket(
                    destination.WorldId,
                    destination.ZoneId,
                    position.X,
                    position.Y,
                    position.Z,
                    destination.World.Rotation.X.DegToRad(),
                    destination.World.Rotation.Y.DegToRad(),
                    yaw
                )
            );

            character.Transform = destination.Clone(character);
        }
        else
        {
            // Same level: the client streams the new area seamlessly and never sends
            // CSInstanceLoaded, so blocking movement here would freeze the player server-side.
            // Move first — SetPosition is a no-op while DisabledSetPosition is set — so the region
            // change updates Transform.ZoneId and hands the unit over to the destination Zone.
            character.SetPosition(position.X, position.Y, position.Z, 0f, 0f, yaw);
            character.Transform.FinalizeTransform();
        }

        // TODO - ErrorMessage
        character.SendPacket(new SCTeleportUnitPacket(TeleportReason.Portal, 0,
            position.X, position.Y, position.Z, yaw));
    }

    public static void DeletePortal(Character owner, byte type, uint id)
    {
        var isPrivate = type != 1;
        var portalInfo = owner.Portals.GetPortalInfo(id);
        if (portalInfo == null) return;
        owner.Portals.RemoveFromBookPortal(portalInfo, isPrivate);
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
