using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;
using NLog;
using System.Text.Json;

namespace AAEmu.Game.Core.Managers;

public class CraftManager : Singleton<CraftManager>, ICraftManager
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private const string RuntimePolicyPath = "Data/aa10-crafting-wave5-policy.json";

    private Dictionary<uint, Craft> _crafts = [];
    private HashSet<uint> _executableCraftIds = [];

    public void Load()
    {
        Logger.Info("Loading crafts...");
        using var connection = SQLite.CreateConnection();
        Load(connection, LoadRuntimePolicy(RuntimePolicyPath));
        Logger.Info(
            "Loaded {0} crafts ({1} enabled, {2} promoted by AA10 crafting policy)",
            _crafts.Count,
            _crafts.Values.Count(craft => craft.Enable),
            _executableCraftIds.Count);
    }

    internal void Load(SqliteConnection connection, IReadOnlySet<uint> executableCraftIds)
    {
        ArgumentNullException.ThrowIfNull(connection);
        ArgumentNullException.ThrowIfNull(executableCraftIds);
        var crafts = new Dictionary<uint, Craft>();

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT id, cast_delay, skill_id, wi_id, milestone_id, req_doodad_id, " +
                "actability_limit, recommend_level, visible_order, enable, products_pack_id, " +
                "use_only_actability, craft_c_category_id, craft_d_category_id, orderable, cost " +
                "FROM crafts ORDER BY id";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var craft = new Craft
                {
                    Id = reader.GetUInt32("id"),
                    CastDelay = reader.GetInt32("cast_delay", 0),
                    SkillId = reader.GetUInt32("skill_id", 0),
                    WiId = reader.GetUInt32("wi_id", 0),
                    MilestoneId = reader.GetUInt32("milestone_id", 0),
                    ReqDoodadId = reader.GetUInt32("req_doodad_id", 0),
                    ActabilityLimit = reader.GetInt32("actability_limit", 0),
                    RecommendLevel = reader.GetInt32("recommend_level", 0),
                    VisibleOrder = reader.GetInt32("visible_order", 0),
                    Enable = reader.GetBoolean("enable"),
                    ProductsPackId = reader.GetUInt32("products_pack_id", 0),
                    UseOnlyActability = reader.GetBoolean("use_only_actability"),
                    CraftCCategoryId = reader.GetUInt32("craft_c_category_id", 0),
                    CraftDCategoryId = reader.GetUInt32("craft_d_category_id", 0),
                    Orderable = reader.GetBoolean("orderable"),
                    Cost = reader.GetInt32("cost", 0)
                };
                crafts.Add(craft.Id, craft);
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT id, craft_id, item_id, amount, rate, use_grade, item_grade_id " +
                "FROM craft_products ORDER BY id";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var craftId = reader.GetUInt32("craft_id");
                if (!crafts.TryGetValue(craftId, out var craft))
                    continue;
                craft.CraftProducts.Add(new CraftProduct
                {
                    Id = reader.GetUInt32("id"),
                    CraftId = craftId,
                    ItemId = reader.GetUInt32("item_id"),
                    Amount = reader.GetInt32("amount", 0),
                    Rate = reader.GetInt32("rate", 0),
                    UseGrade = reader.GetBoolean("use_grade"),
                    ItemGradeId = reader.GetUInt32("item_grade_id", 0)
                });
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT id, craft_id, item_id, amount, main_grade, require_grade, upper_grade " +
                "FROM craft_materials ORDER BY id";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var craftId = reader.GetUInt32("craft_id");
                if (!crafts.TryGetValue(craftId, out var craft))
                    continue;
                craft.CraftMaterials.Add(new CraftMaterial
                {
                    Id = reader.GetUInt32("id"),
                    CraftId = craftId,
                    ItemId = reader.GetUInt32("item_id"),
                    Amount = reader.GetInt32("amount", 0),
                    MainGrade = reader.GetBoolean("main_grade"),
                    RequireGrade = reader.GetInt32("require_grade", -1),
                    UpperGrade = reader.GetBoolean("upper_grade")
                });
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT craft_pack_id, craft_id FROM craft_pack_crafts ORDER BY id";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                if (crafts.TryGetValue(reader.GetUInt32("craft_id"), out var craft))
                    craft.CraftPackIds.Add(reader.GetUInt32("craft_pack_id"));
            }
        }

        var invalidPolicyIds = executableCraftIds
            .Where(id => !crafts.TryGetValue(id, out var craft) || !craft.Enable)
            .OrderBy(id => id)
            .ToArray();
        if (invalidPolicyIds.Length != 0)
            throw new InvalidDataException(
                $"AA10 crafting policy contains {invalidPolicyIds.Length} unknown or disabled recipes.");

        _crafts = crafts;
        _executableCraftIds = executableCraftIds.ToHashSet();
    }

    public bool TryGetCraft(uint craftId, out Craft craft)
    {
        if (_executableCraftIds.Contains(craftId) &&
            _crafts.TryGetValue(craftId, out craft) && craft.Enable)
            return true;
        craft = null;
        return false;
    }

    public bool HasCraft(uint craftId) => TryGetCraft(craftId, out _);

    internal bool TryGetAnyCraft(uint craftId, out Craft craft) => _crafts.TryGetValue(craftId, out craft);

    internal static HashSet<uint> LoadRuntimePolicy(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException(
                "AA10 crafting runtime policy is required; crafting cannot fall back to legacy.", path);

        var policy = JsonSerializer.Deserialize<CraftRuntimePolicy>(
            File.ReadAllText(path),
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        if (policy is null || policy.Format != "aa10-crafting-runtime-policy-v5" ||
            string.IsNullOrWhiteSpace(policy.SourceManifestSha256) ||
            policy.ExecutableCraftIds is null || policy.ExecutableCraftIds.Count == 0)
            throw new InvalidDataException("AA10 crafting runtime policy is invalid or empty.");

        var executable = policy.ExecutableCraftIds.ToHashSet();
        if (executable.Count != policy.ExecutableCraftIds.Count || executable.Contains(0))
            throw new InvalidDataException("AA10 crafting runtime policy contains duplicate or zero IDs.");
        return executable;
    }

    private sealed class CraftRuntimePolicy
    {
        public string Format { get; init; }
        public string SourceManifestSha256 { get; init; }
        public List<uint> ExecutableCraftIds { get; init; }
    }
}
