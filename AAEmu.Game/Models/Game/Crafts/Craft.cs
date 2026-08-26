using AAEmu.Game.Core.Managers;
namespace AAEmu.Game.Models.Game.Crafts;

/*
    Data relating to a craft.
*/
public class Craft
{
    public uint Id { get; set; }
    public int CastDelay { get; set; }
    // 10.0.2.13: ToolId removed
    public uint SkillId { get; set; }
    public uint WiId { get; set; }
    public uint MilestoneId { get; set; }
    public uint ReqDoodadId { get; set; }
    // 10.0.2.13: NeedBind, AcId removed
    public int ActabilityLimit { get; set; }
    // 10.0.2.13: ShowUpperCraft removed
    public int RecommendLevel { get; set; }
    public int VisibleOrder { get; set; }
    public bool Enable { get; set; }
    public int Cost { get; set; }
    public uint ProductsPackId { get; set; }
    public bool UseOnlyActability { get; set; }
    public uint CraftCCategoryId { get; set; }
    public uint CraftDCategoryId { get; set; }
    public bool Orderable { get; set; }

    public List<CraftProduct> CraftProducts { get; set; } = [];
    public List<CraftMaterial> CraftMaterials { get; set; } = [];
    /// <summary>
    /// Catalogue memberships from craft_pack_crafts. These group recipes in the client UI; they do
    /// not say that the crafted product is an auto-equipped backpack.
    /// </summary>
    public HashSet<uint> CraftPackIds { get; } = [];
}
