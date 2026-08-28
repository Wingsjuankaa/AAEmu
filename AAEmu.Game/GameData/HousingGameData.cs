using AAEmu.Commons.IO;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.GameData;

[GameData]
public class HousingGameData : Singleton<HousingGameData>, IGameDataLoader
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    private Dictionary<uint, HousingDecoration> _housingDecorations = [];
    private List<ItemHousingDecoration> _housingItemHousingDecorations = [];
    private List<HousingItemHousings> _housingItemHousings = [];
    private Dictionary<uint, HousingTemplate> _housingTemplates = [];
    private HousingAreaShapeCatalog _housingAreaShapes = HousingAreaShapeCatalog.Empty;
    private HousingInteractionCatalog _housingInteractions = HousingInteractionCatalog.Empty;

    public void Load(SqliteConnection connection)
    {
        _housingTemplates = [];
        _housingItemHousings = [];
        _housingDecorations = [];
        _housingItemHousingDecorations = [];
        _zoneHousingGroups.Clear();
        _areaHousingGroups.Clear();
        _groupCategories.Clear();
        _housingAreaShapes = HousingAreaShapeCatalog.Empty;
        _housingInteractions = HousingInteractionCatalog.Empty;

        // var houseTaxes = new Dictionary<uint, HouseTax>();

        Logger.Info("Loading Housing Information ...");

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM housing_areas WHERE activated = 't'";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var areaId = reader.GetUInt32("id", 0);
                    var housingGroupId = reader.GetUInt32("housing_group_id", 0);
                    if (areaId > 0 && housingGroupId > 0)
                        _areaHousingGroups[areaId] = housingGroupId;
                    var zoneName = reader.GetString("name", string.Empty);
                    if (string.IsNullOrEmpty(zoneName))
                        continue;
                    if (!_zoneHousingGroups.TryGetValue(zoneName, out var groups))
                        _zoneHousingGroups[zoneName] = groups = [];
                    groups.Add(housingGroupId);
                }
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM housing_group_categories";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var group = reader.GetUInt32("housing_group_id", 0);
                    if (!_groupCategories.TryGetValue(group, out var categories))
                        _groupCategories[group] = categories = [];
                    categories.Add(reader.GetUInt32("category_id", 0));
                }
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM item_housings";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var template = new HousingItemHousings
                    {
                        Id = reader.GetUInt32("id"),
                        Item_Id = reader.GetUInt32("item_id"),
                        Design_Id = reader.GetUInt32("design_id"),
                        Completion = reader.GetBoolean("completion", false)
                    };
                    _housingItemHousings.Add(template);
                }
            }
        }

        Logger.Info("Loading Housing Templates...");
        // Define the folder path where your housing binding files reside.
        var dataFolder = Path.Combine(FileManager.AppPath, "Data");

        LoadHousingInteractionCatalog(dataFolder);
        LoadHousingAreaShapes(dataFolder);

        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                                  SELECT h.*, s.garden_radius
                                  FROM housings h
                                  JOIN housing_sizes s ON s.id = h.housing_size_id
                                  """;
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var template = new HousingTemplate
                    {
                        Id = reader.GetUInt32("id"),
                        Name = reader.GetString("name"),
                        CategoryId = reader.GetUInt32("category_id"),
                        MainModelId = reader.GetUInt32("main_model_id"),
                        DoorModelId = reader.GetUInt32("door_model_id", 0),
                        StairModelId = reader.GetUInt32("stair_model_id", 0),
                        AutoZ = reader.GetBoolean("auto_z", true),
                        GateExists = reader.GetBoolean("gate_exists", true),
                        Hp = reader.GetInt32("hp"),
                        RepairCost = reader.GetUInt32("repair_cost"),
                        Family = reader.GetString("family"),
                        TaxationId = reader.GetUInt32("taxation_id"),
                        GuardTowerSettingId = reader.GetUInt32("guard_tower_setting_id", 0),
                        CinemaRadius = reader.GetFloat("cinema_radius"),
                        AutoZOffsetX = reader.GetFloat("auto_z_offset_x"),
                        AutoZOffsetY = reader.GetFloat("auto_z_offset_y"),
                        AutoZOffsetZ = reader.GetFloat("auto_z_offset_z"),
                        Alley = reader.GetFloat("alley"),
                        ExtraHeightAbove = reader.GetFloat("extra_height_above"),
                        ExtraHeightBelow = reader.GetFloat("extra_height_below"),
                        DecoLimit = reader.GetUInt32("deco_limit"),
                        AbsoluteDecoLimit = reader.GetUInt32("absolute_deco_limit"),
                        HousingDecoLimitId = reader.GetUInt32("housing_deco_limit_id", 0),
                        IsSellable = reader.GetBoolean("is_sellable", true),
                        HeavyTax = reader.GetBoolean("heavy_tax", true),
                        AlwaysPublic = reader.GetBoolean("always_public", true),
                        HousingSizeId = reader.GetUInt32("housing_size_id"),
                        GardenRadius = reader.GetFloat("garden_radius")
                    };
                    _housingTemplates.Add(template.Id, template);

                    using (var command2 = connection.CreateCommand())
                    {
                        command2.CommandText = "SELECT * FROM housing_binding_doodads WHERE housing_id=@housing_id";
                        command2.Parameters.AddWithValue("housing_id", template.Id);
                        command2.Prepare();
                        using (var reader2 = new SQLiteWrapperReader(command2.ExecuteReader()))
                        {
                            var definitions = new List<HousingBindingDefinition>();
                            while (reader2.Read())
                            {
                                var attachPointId = (AttachPointKind)reader2.GetInt16("attach_point_id");
                                var doodadId = reader2.GetUInt32("doodad_id");
                                var forceDbSave = reader2.GetBoolean("force_db_save", false);

                                if (_housingInteractions.TryGetDefinition(
                                        template.Id, (byte)attachPointId, doodadId, out var definition) &&
                                    definition.ForceDbSave == forceDbSave)
                                {
                                    definitions.Add(definition);
                                    continue;
                                }

                                definitions.Add(new HousingBindingDefinition
                                {
                                    HousingTemplateId = template.Id,
                                    AttachPointId = attachPointId,
                                    DoodadId = doodadId,
                                    ForceDbSave = forceDbSave,
                                    BlockReason = HousingInteractionBlockReason.CatalogMismatch
                                });
                            }

                            template.HousingBindings = definitions.AsReadOnly();
                        }
                    }
                }
            }
        }

        Logger.Info($"Loaded Housing Templates {_housingTemplates.Count}");
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM housing_build_steps";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var housingId = reader.GetUInt32("housing_id");
                    if (!_housingTemplates.ContainsKey(housingId))
                        continue;

                    var template = new HousingBuildStep
                    {
                        Id = reader.GetUInt32("id"),
                        HousingId = housingId,
                        Step = reader.GetInt16("step"),
                        ModelId = reader.GetUInt32("model_id"),
                        SkillId = reader.GetUInt32("skill_id"),
                        NumActions = reader.GetInt32("num_actions")
                    };

                    _housingTemplates[housingId].BuildSteps.Add(template.Step, template);
                }
            }
        }

        Logger.Info("Loaded Decoration Templates...");
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM housing_decorations";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var template = new HousingDecoration
                    {
                        Id = reader.GetUInt32("id"),
                        Name = reader.GetString("name"),
                        AllowOnFloor = reader.GetBoolean("allow_on_floor"),
                        AllowOnWall = reader.GetBoolean("allow_on_wall"),
                        AllowOnCeiling = reader.GetBoolean("allow_on_ceiling"),
                        DoodadId = reader.GetUInt32("doodad_id"),
                        // 10.0.2.13: allow_pivot_on_garden removed
                        ActabilityGroupId =
                            !reader.IsDBNull("actability_group_id") ? reader.GetUInt32("actability_group_id") : 0,
                        ActabilityUp = !reader.IsDBNull("actability_up") ? reader.GetUInt32("actability_up") : 0,
                        DecoActAbilityGroupId =
                            !reader.IsDBNull("deco_actability_group_id")
                                ? reader.GetUInt32("deco_actability_group_id")
                                : 0
                        // 10.0.2.13: allow_mesh_on_garden removed
                    };

                    _housingDecorations.Add(template.Id, template);
                }
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM item_housing_decorations";
            command.Prepare();
            using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
            {
                while (reader.Read())
                {
                    var template = new ItemHousingDecoration
                    {
                        Id = reader.GetUInt32("id"),
                        ItemId = reader.GetUInt32("item_id"),
                        DesignId = reader.GetUInt32("design_id"),
                        Restore = reader.GetBoolean("restore", true)
                    };
                    _housingItemHousingDecorations.Add(template);
                }
            }
        }

    }

    public void PostLoad()
    {
        foreach (var (_, template) in _housingTemplates)
        {
            template.Name = LocalizationManager.Instance.Get("housings", "name", template.Id, template.Name);
            template.Taxation = TaxationsManager.Instance.taxations.GetValueOrDefault(template.TaxationId);
        }

    }

    private void LoadHousingInteractionCatalog(string dataFolder)
    {
        var filePath = Path.Combine(dataFolder, "housing_interactions_aa10_h3.json");
        if (!File.Exists(filePath))
        {
            Logger.Error("AA10 housing interaction catalogue is missing; every structural binding will fail closed.");
            return;
        }

        var contents = FileManager.GetFileContents(filePath);
        if (string.IsNullOrWhiteSpace(contents) ||
            !JsonHelper.TryDeserializeObject(contents, out HousingInteractionCatalogFile catalogFile, out _) ||
            catalogFile?.SchemaVersion != HousingInteractionCatalog.CurrentSchemaVersion ||
            catalogFile.Bindings is null)
        {
            Logger.Error("AA10 housing interaction catalogue is invalid; every structural binding will fail closed.");
            return;
        }

        try
        {
            _housingInteractions = HousingInteractionCatalog.Create(catalogFile.Bindings);
            Logger.Info(
                $"Loaded AA10 housing interaction catalogue: {_housingInteractions.BindingCount} bindings, " +
                $"{_housingInteractions.HousingTemplateCount} housing templates");
        }
        catch (InvalidDataException ex)
        {
            _housingInteractions = HousingInteractionCatalog.Empty;
            Logger.Error(ex, "AA10 housing interaction catalogue contains duplicate identities; bindings fail closed.");
        }
    }

    private void LoadHousingAreaShapes(string dataFolder)
    {
        var filePath = Path.Combine(dataFolder, "housing_area_shapes_aa10_h1.json");
        if (!File.Exists(filePath))
        {
            Logger.Error("AA10 housing area catalogue is missing; new placements will fail closed.");
            return;
        }

        var contents = FileManager.GetFileContents(filePath);
        if (string.IsNullOrWhiteSpace(contents) ||
            !JsonHelper.TryDeserializeObject(contents, out HousingAreaShapeFile shapeFile, out _) ||
            shapeFile?.SchemaVersion != 1 || shapeFile.Shapes is null)
        {
            Logger.Error("AA10 housing area catalogue is invalid; new placements will fail closed.");
            return;
        }

        _housingAreaShapes = HousingAreaShapeCatalog.Create(shapeFile.Shapes);
        Logger.Info(
            $"Loaded AA10 housing area catalogue: {_housingAreaShapes.ShapeCount} shapes, " +
            $"{_housingAreaShapes.AreaCount} areas, {_housingAreaShapes.WorldCount} worlds");
    }

    /// <summary>
    /// Gets a template by it's design Id
    /// </summary>
    /// <param name="designId"></param>
    /// <returns></returns>
    /// <summary>zone name -> housing groups whose areas are activated there (housing_areas).</summary>
    private readonly Dictionary<string, HashSet<uint>> _zoneHousingGroups = [];

    /// <summary>housing_areas.id -> housing_group_id for exact client polygons.</summary>
    private readonly Dictionary<uint, uint> _areaHousingGroups = [];

    /// <summary>housing group -> house categories it permits (housing_group_categories).</summary>
    private readonly Dictionary<uint, HashSet<uint>> _groupCategories = [];

    /// <summary>
    /// True when a house of <paramref name="categoryId"/> may be built in the named zone.
    /// </summary>
    /// <remarks>
    /// housing_areas names the zone a group's areas sit in, and housing_group_categories says which
    /// house categories each group permits, so a zone with no activated area rejects everything and a
    /// zone that only hosts farm groups rejects a manor. This is the coarse half of the rule: the
    /// exact buildable outlines are LevelDesignShape objects in packed level data, which only the
    /// zone loads, so a position inside the right zone but outside a shape still passes here.
    ///
    /// going away. Nothing in the zone judges a placement, so a shape-accurate test has to read the
    /// LevelDesignShape geometry rather than wait for the zone to object.
    /// </remarks>
    public bool IsCategoryAllowedInZone(string zoneName, uint categoryId)
    {
        if (string.IsNullOrEmpty(zoneName) || !_zoneHousingGroups.TryGetValue(zoneName, out var groups))
            return false;

        foreach (var group in groups)
            if (_groupCategories.TryGetValue(group, out var categories) && categories.Contains(categoryId))
                return true;

        return false;
    }

    public bool IsCategoryAllowedForFootprint(
        string worldName,
        double x,
        double y,
        double radius,
        uint categoryId) =>
        HousingPlacementPolicy.IsCategoryAllowedForFootprint(
            worldName,
            x,
            y,
            radius,
            categoryId,
            _housingAreaShapes,
            _areaHousingGroups,
            _groupCategories);

    public HousingItemHousings FindAuthorizedDesignItem(
        uint designId,
        uint itemTemplateId,
        ulong itemOwnerId,
        uint characterId) =>
        HousingPlacementPolicy.FindAuthorizedDesignItem(
            designId,
            itemTemplateId,
            itemOwnerId,
            characterId,
            _housingItemHousings);

    public HousingTemplate GetTemplate(uint designId)
    {
        return _housingTemplates.GetValueOrDefault(designId);
    }

    public bool TryGetBindings(
        uint housingTemplateId,
        out IReadOnlyList<HousingBindingDefinition> bindings) =>
        _housingInteractions.TryGetBindings(housingTemplateId, out bindings);

    /// <summary>
    /// Gets data for the item for a housing decoration
    /// </summary>
    /// <param name="decoDesignId"></param>
    /// <returns></returns>
    public ItemHousingDecoration GetItemHousingDecorations(uint decoDesignId)
    {
        return _housingItemHousingDecorations.Find(x => x.DesignId == decoDesignId);
    }

    public bool IsAuthorizedDecorationItem(uint designId, uint itemTemplateId) =>
        _housingItemHousingDecorations.Any(mapping =>
            mapping.DesignId == designId && mapping.ItemId == itemTemplateId);

    /// <summary>
    /// Get original item template based on house design
    /// </summary>
    /// <param name="designId"></param>
    /// <returns></returns>
    public uint GetItemIdByDesign(uint designId)
    {
        var designs = _housingItemHousings.Where(h => h.Design_Id == designId);
        foreach (var design in designs)
        {
            if (ItemManager.Instance.GetTemplate(design.Item_Id) != null)
                return design.Item_Id;
        }
        return 0;
    }

    /// <summary>
    /// Get decoration design by Id
    /// </summary>
    /// <param name="designId"></param>
    /// <returns></returns>
    public HousingDecoration GetDecorationDesignFromId(uint designId)
    {
        return _housingDecorations.GetValueOrDefault(designId);
    }

    /// <summary>
    /// Get decoration design from it's doodad counterpart
    /// </summary>
    /// <param name="doodadId"></param>
    /// <returns></returns>
    public HousingDecoration GetDecorationDesignFromDoodadId(uint doodadId)
    {
        return _housingDecorations.FirstOrDefault(x => x.Value.DoodadId == doodadId).Value;
    }
}
