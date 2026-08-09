using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Game.Skills.Plots.UpdateTargetMethods
{
    public class PlotTargetAreaParams : IPlotTargetParams
    {
        public AreaShape Shape { get; set; } // TODO: Change to AreaShape object
        public int MaxTargets { get; set; }
        public int Distance { get; set; }
        public int Angle { get; set; }
        public int HeightOffset { get; set; }
        public int UnkValue { get; set; } // Possibly Radius
        public bool HitOnce { get; set; }
        public SkillTargetRelation UnitRelationType { get; set; }
        public byte UnitTypeFlag { get; set; }

        public bool CarriesPreviousTarget =>
            MaxTargets == 0 &&
            Distance == 0 &&
            Angle == 0 &&
            HeightOffset == 0 &&
            UnkValue == 0 &&
            Shape != null &&
            Shape.Type == AreaShapeType.Sphere &&
            Shape.Value1 == 0f &&
            Shape.Value2 == 0f &&
            Shape.Value3 == 0f;


        public PlotTargetAreaParams(PlotEventTemplate template)
        {
            Shape = ResolveShape(
                WorldManager.Instance.GetAreaShapeById((uint)template.TargetUpdateMethodParam1),
                template.TargetUpdateMethodParam6);
            MaxTargets = template.TargetUpdateMethodParam2;
            Distance = template.TargetUpdateMethodParam3;
            Angle = template.TargetUpdateMethodParam4;
            HeightOffset = template.TargetUpdateMethodParam5;
            UnkValue = template.TargetUpdateMethodParam6;
            HitOnce = template.TargetUpdateMethodParam7 == 1;
            UnitRelationType = (SkillTargetRelation)template.TargetUpdateMethodParam8;
            UnitTypeFlag = (byte)template.TargetUpdateMethodParam9;
        }

        public static AreaShape ResolveShape(AreaShape source, int radiusMillimeters)
        {
            if (source == null || source.Type != AreaShapeType.Sphere ||
                source.Value1 > 0f || radiusMillimeters <= 0)
                return source;

            // AA8/AA10 plot rows reuse a zero-radius sphere descriptor and
            // carry the event-specific radius in param6 (millimetres).  Copy
            // the shared descriptor so one event cannot mutate another.
            return new AreaShape
            {
                Id = source.Id,
                Type = source.Type,
                Value1 = radiusMillimeters / 1000f,
                Value2 = source.Value2,
                Value3 = source.Value3
            };
        }
    }
}
