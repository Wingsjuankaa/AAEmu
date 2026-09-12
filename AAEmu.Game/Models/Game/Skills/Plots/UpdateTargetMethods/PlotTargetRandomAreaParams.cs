using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Game.Skills.Plots.UpdateTargetMethods;

public class PlotTargetRandomAreaParams(PlotEventTemplate template) : IPlotTargetParams
{
    public AreaShape Shape { get; set; } = WorldManager.Instance.GetAreaShapeById((uint)template.TargetUpdateMethodParam1); // TODO: Change to AreaShape object
    public int MaxTargets { get; set; } = template.TargetUpdateMethodParam2;
    public int Distance { get; set; } = template.TargetUpdateMethodParam3;
    // p4 is not Area.p5's additive height. Plot 2957 and the retail video expose
    // the erroneous +8m lift; AA10 test plot130 separates horizontal/vertical random areas.
    // Its full terrain-probe semantics remain unresolved; preserve the raw value.
    public int Param4 { get; set; } = template.TargetUpdateMethodParam4;
    public int UnkValue { get; set; } = template.TargetUpdateMethodParam5; //Possibly Radius?
    public bool HitOnce { get; set; } = template.TargetUpdateMethodParam6 == 1;
    public SkillTargetRelation UnitRelationType { get; set; } = (SkillTargetRelation)template.TargetUpdateMethodParam7; // TODO: Change to enum
    public byte UnitTypeFlag { get; set; } = (byte)template.TargetUpdateMethodParam8;
}
