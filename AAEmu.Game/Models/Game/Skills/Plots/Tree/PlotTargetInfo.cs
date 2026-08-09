using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Skills.Plots.UpdateTargetMethods;
using AAEmu.Game.Models.Game.Skills.Utils;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Mechanics;
using AAEmu.Game.Utils;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Plots.Tree
{
    public class PlotTargetInfo
    {
        private Logger _log = NLog.LogManager.GetCurrentClassLogger();

        public BaseUnit Source { get; set; }
        private BaseUnit PreviousSource { get; set; }
        public BaseUnit Target { get; set; }
        private BaseUnit PreviousTarget { get; set; }
        public List<BaseUnit> EffectedTargets { get; set; }

        public PlotTargetInfo(PlotState state)
        {
            EffectedTargets = new List<BaseUnit>();
            PreviousSource = state.Caster;
            PreviousTarget = state.Target;
        }

        public PlotTargetInfo(BaseUnit source, BaseUnit target)
        {
            EffectedTargets = new List<BaseUnit>();
            PreviousSource = source;
            PreviousTarget = target;
            Source = source;
            Target = target;
        }

        public void UpdateTargetInfo(PlotEventTemplate template, PlotState state)
        {
            UpdateSource(template, state);
            UpdateTargets(template, state);
        }
        
        public void UpdateSource(PlotEventTemplate template, PlotState state)
        {
            switch ((PlotSourceUpdateMethodType)template.SourceUpdateMethodId)
            {
                case PlotSourceUpdateMethodType.OriginalSource:
                    Source = state.Caster;
                    break;
                case PlotSourceUpdateMethodType.OriginalTarget:
                    Source = state.Target;
                    break;
                case PlotSourceUpdateMethodType.PreviousSource:
                    Source = PreviousSource;
                    break;
                case PlotSourceUpdateMethodType.PreviousTarget:
                    Source = PreviousTarget;
                    break;
            }
        }

        public void UpdateTargets(PlotEventTemplate template, PlotState state)
        {
            switch ((PlotTargetUpdateMethodType)template.TargetUpdateMethodId)
            {
                case PlotTargetUpdateMethodType.OriginalSource:
                    Target = state.Caster;
                    EffectedTargets.Add(Target);
                    break;
                case PlotTargetUpdateMethodType.OriginalTarget:
                    Target = state.Target;
                    EffectedTargets.Add(Target);
                    break;
                case PlotTargetUpdateMethodType.PreviousSource:
                    Target = PreviousSource;
                    EffectedTargets.Add(Target);
                    break;
                case PlotTargetUpdateMethodType.PreviousTarget:
                    Target = PreviousTarget;
                    EffectedTargets.Add(Target);
                    break;
                case PlotTargetUpdateMethodType.Area:
                    Target = UpdateAreaTarget(new PlotTargetAreaParams(template), state, template);
                    break;
                case PlotTargetUpdateMethodType.RandomUnit:
                    Target = UpdateRandomUnitTarget(new PlotTargetRandomUnitParams(template), state, template);
                    break;
                case PlotTargetUpdateMethodType.RandomArea:
                    Target = UpdateRandomAreaTarget(new PlotTargetRandomAreaParams(template), state, template);
                    break;
            }
        }

        private BaseUnit UpdateAreaTarget(PlotTargetAreaParams args, PlotState state, PlotEventTemplate plotEvent)
        {
            BaseUnit posUnit = new BaseUnit();
            posUnit.ObjId = uint.MaxValue;
            posUnit.Region = PreviousTarget.Region;
            posUnit.Transform = PreviousTarget.Transform.CloneDetached(posUnit);
            var degrees = (float)args.Angle;
            posUnit.Transform.Local.Rotate(0,0,degrees.DegToRad() * -1f);
            // posUnit.Transform.Local.Rotate(Quaternion.CreateFromYawPitchRoll(((float)args.Angle).DegToRad() * -1f, 0f, 0f));
            if (args.Distance != 0)
            {
                posUnit.Transform.Local.AddDistanceToFront(args.Distance / 1000f - 0.01f);
            }
            posUnit.Transform.Local.SetHeight(Math.Max(PreviousTarget.Transform.World.Position.Z + args.HeightOffset / 1000f,WorldManager.Instance.GetHeight(posUnit.Transform)));
            // posUnit.Transform.Local.SetHeight(WorldManager.Instance.GetHeight(posUnit.Transform));

            if (args.MaxTargets == 0)
            {
                EffectedTargets.Add(posUnit);
                return posUnit;
            }
            
            // posUnit.Position.Z = get heightmap value for x:y     
            //TODO: Get Targets around posUnit?
            var unitsInRange = FilterTargets(GetAroundByShape(posUnit, args.Shape), state, args, plotEvent);
            unitsInRange = TakeDeterministicAreaTargets(unitsInRange, PreviousTarget, args.MaxTargets);
            // TODO : Filter min distance
            // TODO : Compute Unit Relation
            // TODO : Compute Unit Flag
            // unitsInRange = unitsInRange.Where(u => u.);

            EffectedTargets.AddRange(unitsInRange);
            if (state.HitObjects.ContainsKey(plotEvent.Id))
            {
                state.HitObjects[plotEvent.Id].AddRange(unitsInRange);
            }
            else
            {
                state.HitObjects.Add(plotEvent.Id, new List<GameObject>(unitsInRange));
            }

            return posUnit;
        }

        private BaseUnit UpdateRandomUnitTarget(PlotTargetRandomUnitParams args, PlotState state, PlotEventTemplate plotEvent)
        {
            var randomUnits = GetAroundByShape(Source, args.Shape).ToList();

            // A zero-volume AA8 shape is a point selector. Region queries
            // intentionally omit their origin, but native plots use these
            // selectors to carry the current source into the next branch
            // (Ollo's Hammer 18757 is the first proven consumer). Include the
            // origin before applying the native relation/type filters.
            if (args.IsPointSelector && Source is Unit sourceUnit &&
                randomUnits.All(unit => unit.ObjId != sourceUnit.ObjId))
                randomUnits.Add(sourceUnit);

            var filteredUnits = FilterTargets(randomUnits, state, args, plotEvent);
            if (args.HitOnce)
                filteredUnits = filteredUnits.Where(unit => unit.ObjId != PreviousTarget.ObjId);

            var materialized = filteredUnits.ToList();
            if (materialized.Count == 0)
                return null;

            var index = Rand.Next(0, materialized.Count);
            var randomUnit = materialized[index];

            EffectedTargets.Add(randomUnit);
            if (state.HitObjects.ContainsKey(plotEvent.Id))
            {
                state.HitObjects[plotEvent.Id].Add(randomUnit);
            }
            else
            {
                state.HitObjects.Add(plotEvent.Id, new List<GameObject>{ randomUnit });
            }

            return randomUnit;
        }

        private BaseUnit UpdateRandomAreaTarget(PlotTargetRandomAreaParams args, PlotState state, PlotEventTemplate plotEvent)
        {
            BaseUnit posUnit = new BaseUnit();
            posUnit.ObjId = uint.MaxValue;
            posUnit.Region = PreviousTarget.Region;
            posUnit.Transform = PreviousTarget.Transform.CloneDetached(posUnit);
            posUnit.Transform.ZoneId = PreviousTarget.Transform.ZoneId;
            posUnit.Transform.WorldId = PreviousTarget.Transform.WorldId;
            posUnit.Transform.Local.SetZRotation(((float)Rand.Next(-180, 180)).DegToRad());
            posUnit.Transform.Local.AddDistanceToFront(ResolveRandomAreaDistance(
                args.Distance,
                Rand.NextSingle()));
            var previousHeight = PreviousTarget.Transform.World.Position.Z;
            var terrainHeight = WorldManager.Instance.GetHeight(posUnit.Transform);
            posUnit.Transform.Local.SetHeight(ResolveRandomAreaHeight(
                previousHeight,
                terrainHeight,
                args.TerrainCorrectionLimit,
                AppConfiguration.Instance.HeightMapsEnable));
            //posUnit.Transform.Local.SetHeight(WorldManager.Instance.GetHeight(posUnit.Transform));

            if (args.MaxTargets == 0)
            {
                EffectedTargets.Add(posUnit);
                return posUnit;
            }

            // posUnit.Position.Z = get heightmap value for x:y     
            //TODO: Get Targets around posUnit?
            var unitsInRange = FilterTargets(GetAroundByShape(posUnit, args.Shape), state, args, plotEvent);
            unitsInRange = TakeDeterministicAreaTargets(unitsInRange, PreviousTarget, args.MaxTargets);

            // TODO : Filter min distance
            // TODO : Compute Unit Relation
            // TODO : Compute Unit Flag
            // unitsInRange = unitsInRange.Where(u => u.);

            EffectedTargets.AddRange(unitsInRange);
            if (state.HitObjects.ContainsKey(plotEvent.Id))
            {
                state.HitObjects[plotEvent.Id].AddRange(unitsInRange);
            }
            else
            {
                state.HitObjects.Add(plotEvent.Id, new List<GameObject>(unitsInRange));
            }

            return posUnit;
        }

        public static float ResolveRandomAreaHeight(
            float previousHeight,
            float terrainHeight,
            int terrainCorrectionLimitMillimeters,
            bool heightMapsEnabled)
        {
            if (!heightMapsEnabled)
                return previousHeight;

            var correctionLimit = Math.Abs(terrainCorrectionLimitMillimeters) / 1000f;
            return Math.Abs(terrainHeight - previousHeight) <= correctionLimit
                ? terrainHeight
                : previousHeight;
        }

        public static float ResolveRandomAreaDistance(
            int maximumDistanceMillimeters,
            float normalizedSample)
        {
            var maximumDistance = Math.Abs(maximumDistanceMillimeters) / 1000f;
            var sample = Math.Max(0f, Math.Min(1f, normalizedSample));
            return maximumDistance * sample;
        }

        private static IEnumerable<Unit> GetAroundByShape(GameObject origin, AreaShape shape)
        {
            var labWorld = MechanicsRuntime.Current?.World;
            return labWorld != null
                ? labWorld.GetAroundByShape(origin, shape).OfType<Unit>()
                : WorldManager.Instance.GetAroundByShape<Unit>(origin, shape);
        }

        private IEnumerable<Unit> FilterTargets(IEnumerable<Unit> units, PlotState state, IPlotTargetParams args, PlotEventTemplate plotEvent)
        {
            var template = state.ActiveSkill.Template;
            var filtered = units;
            if (!template.TargetAlive)
                filtered = filtered.Where(o => o.Hp == 0);
            if (!template.TargetDead)
                filtered = filtered.Where(o => o.Hp > 0);
            if (args.HitOnce)
            {
                filtered = filtered.Where(o =>
                {
                    if (state.HitObjects.ContainsKey(plotEvent.Id))
                        return !state.HitObjects[plotEvent.Id].Contains(o);
                    else
                        return true;
                });
            }
            
            filtered = SkillTargetingUtil.FilterWithRelation(args.UnitRelationType, state.Caster, filtered);
            if (args.UnitTypeFlag != 0)
                filtered = filtered.Where(o => ((byte)o.TypeFlag & args.UnitTypeFlag) != 0);
            if (plotEvent.AoeConditions.Count > 0)
                filtered = filtered.Where(
                    unit => plotEvent.AoeConditions.All(condition => condition.CheckCondition(state, unit)));

            return filtered;
        }

        public static IEnumerable<Unit> TakeDeterministicAreaTargets(
            IEnumerable<Unit> candidates,
            BaseUnit primaryTarget,
            int maxTargets)
        {
            var primaryId = primaryTarget?.ObjId ?? 0;
            var primaryPosition = primaryTarget?.Transform?.World.Position;
            var ordered = candidates
                .Where(unit => unit != null)
                .GroupBy(unit => unit.ObjId)
                .Select(group => group.First())
                .OrderBy(unit => unit.ObjId == primaryId ? 0 : 1)
                .ThenBy(unit =>
                {
                    if (primaryPosition == null || unit.Transform == null)
                        return 0f;
                    var position = unit.Transform.World.Position;
                    var dx = position.X - primaryPosition.Value.X;
                    var dy = position.Y - primaryPosition.Value.Y;
                    return dx * dx + dy * dy;
                })
                .ThenBy(unit => unit.ObjId);

            return maxTargets > 0 ? ordered.Take(maxTargets) : ordered;
        }
    }
}
