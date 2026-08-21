using AAEmu.Game.Models.Game.World.Zones;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.Game.Models.Game.DoodadObj.Templates;

public class DoodadTemplate
{
    public uint Id { get; set; }
    public bool OnceOneMan { get; set; }
    public bool OnceOneInteraction { get; set; }
    public bool MgmtSpawn { get; set; }
    /// <summary>
    /// True when retail authored the placement in client world data. Most remain client-local,
    /// but npctype-backed quest actors require a World instance so the client receives a usable
    /// object id and the server can validate quest interaction.
    /// </summary>
    public bool ClientDoodad { get; set; }
    public int Percent { get; set; }
    public int MinTime { get; set; }
    public int MaxTime { get; set; }
    public uint ModelKindId { get; set; }
    /// <summary>URI from doodad_almighties.model (cgf://, vegetation://, prefab://, …).</summary>
    public string Model { get; set; } = "";
    /// <summary>When true, Zone pulls mesh from world/level instead of packet modelId.</summary>
    public bool LoadModelFromWorld { get; set; }
    public bool UseCreatorFaction { get; set; }
    public bool ForceTodTopPriority { get; set; }
    public uint MilestoneId { get; set; }
    public uint GroupId { get; set; }
    public bool UseTargetDecal { get; set; }
    public bool UseTargetSilhouette { get; set; }
    public bool UseTargetHighlight { get; set; }
    public float TargetDecalSize { get; set; }
    public int SimRadius { get; set; }
    public bool CollideShip { get; set; }
    public bool CollideVehicle { get; set; }
    public Climate ClimateId { get; set; }
    public bool SaveIndun { get; set; }
    public bool ForceUpAction { get; set; }
    public bool Parentable { get; set; }
    public bool Childable { get; set; }
    public FactionsEnum FactionId { get; set; }
    public int GrowthTime { get; set; }
    public bool DespawnOnCollision { get; set; }
    public bool NoCollision { get; set; }
    public uint RestrictZoneId { get; set; }

    public List<DoodadFuncGroups> FuncGroups { get; set; } = [];

    /// <summary>
    /// Returns the native phase that makes a client-authored doodad act as an NPC. Retail data
    /// normally places the npctype model in a Normal group, with Start used as a fallback by a
    /// smaller set of templates.
    /// </summary>
    public DoodadFuncGroups GetNpcProxyFuncGroup()
    {
        if (!ClientDoodad)
            return null;

        static bool IsNpcProxy(DoodadFuncGroups group) =>
            group.Model?.StartsWith("npctype://", StringComparison.OrdinalIgnoreCase) == true;

        return FuncGroups.FirstOrDefault(group =>
                   group.GroupKindId == DoodadFuncGroups.DoodadFuncGroupKind.Normal && IsNpcProxy(group))
               ?? FuncGroups.FirstOrDefault(group =>
                   group.GroupKindId == DoodadFuncGroups.DoodadFuncGroupKind.Start && IsNpcProxy(group));
    }

    // Helper Properties
    public int TotalDoodadGrowthTime { get; set; }

    /// <summary>
    /// There's probably a better why to check this
    /// </summary>
    /// <returns>Returns true if the GroupId is one of ones that give vocation badges when used</returns>
    public bool GrantsVocationWhenUsed()
    {
        return (DoodadGroupId)GroupId switch
        {
            DoodadGroupId.Deforestation or DoodadGroupId.Picking or DoodadGroupId.Mining or
            DoodadGroupId.Livestock or DoodadGroupId.Agriculture or DoodadGroupId.Excavation or
            DoodadGroupId.MarineAgriculture or DoodadGroupId.SportFishing => true,
            _ => false,
        };
    }
}
