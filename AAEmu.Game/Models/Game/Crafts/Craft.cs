using AAEmu.Game.Models.Game.Items.Templates;
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
    public uint ProductsPackId { get => ProductPackId ?? 0; set => ProductPackId = value == 0 ? null : value; }
    public bool UseOnlyActability { get; set; }
    public uint? CraftCCategoryId { get; set; }
    public uint? CraftDCategoryId { get; set; }
    public bool Orderable { get; set; }

    /// <summary>
    /// Set only by the closed AA10 runtime policy for recipes whose empty material list is an
    /// intentional contract. An empty list remains invalid for every other recipe.
    /// </summary>
    public bool AllowEmptyMaterials { get; internal set; }

    /// <summary>Craft orders may name this craft as the work they want done.</summary>

    /// <summary>Money the craft order board charges for this craft, in copper.</summary>

    /// <summary>
    /// Actability group this craft belongs to, taken from its skill. Zero when the craft's skill is
    /// missing or names no group; the board's actability filter skips such crafts.
    /// </summary>
    public uint ActabilityGroupId { get; set; }

    /// <summary>Whether the shipped craft row is restricted to actability use.</summary>

    /// <summary>
    /// Optional product-pack reference stored on the craft row. The current 10.0.2.13 compact
    /// catalog has no product-pack table, so consumers must not infer a join from this value.
    /// </summary>
    public uint? ProductPackId { get; set; }


    public List<CraftProduct> CraftProducts { get; set; } = [];
    public List<CraftMaterial> CraftMaterials { get; set; } = [];
    public List<CraftLineComponent> CraftLineComponents { get; set; } = [];
    public HashSet<uint> CraftPackIds { get; set; } = [];
    public bool IsPack { get; set; }

    public bool ResultsInBackpack
    {
        get
        {
            return CraftProducts.Select(product => ItemManager.Instance.GetTemplate(product.ItemId))
                .OfType<BackpackTemplate>().Any();
        }
    }
}
