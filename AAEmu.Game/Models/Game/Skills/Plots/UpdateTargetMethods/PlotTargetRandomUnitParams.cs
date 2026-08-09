using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Game.Skills.Plots.UpdateTargetMethods
{
    public class PlotTargetRandomUnitParams : IPlotTargetParams
    {
        public AreaShape Shape { get; set; } // TODO: Change to AreaShape object
        public bool HitOnce { get; set; }
        public SkillTargetRelation UnitRelationType { get; set; } // TODO: Change to enum
        public byte UnitTypeFlag { get; set; }

        public PlotTargetRandomUnitParams(PlotEventTemplate template)
        {
            Shape = WorldManager.Instance.GetAreaShapeById((uint)template.TargetUpdateMethodParam1);
            // AA8/AA10 exact plot rows keep the spatial parameters in 2..6;
            // the selector contract lives in 7..9.  The legacy mapping to
            // 2..4 interpreted max-target/distance/angle as booleans and
            // relation flags, which made valid plot branches disappear.
            HitOnce = template.TargetUpdateMethodParam7 == 1;
            UnitRelationType = (SkillTargetRelation)template.TargetUpdateMethodParam8;
            UnitTypeFlag = (byte)template.TargetUpdateMethodParam9;
        }

        public bool IsPointSelector =>
            Shape != null && Shape.Value1 == 0f && Shape.Value2 == 0f && Shape.Value3 == 0f;
    }
}
