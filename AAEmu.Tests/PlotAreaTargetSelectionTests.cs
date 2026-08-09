using System.Collections.Generic;
using System.Linq;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Plots.UpdateTargetMethods;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotAreaTargetSelectionTests
    {
        private static Unit UnitAt(uint objId, float x, float y)
        {
            var unit = new Unit { ObjId = objId };
            unit.Transform.Local.SetPosition(x, y, 0f);
            return unit;
        }

        [Fact]
        public void PrimaryTargetIsIncludedFirstAndOnlyOnce()
        {
            var primary = UnitAt(20, 10f, 10f);
            var near = UnitAt(21, 10.5f, 10f);
            var far = UnitAt(22, 12f, 10f);

            var result = PlotTargetInfo.TakeDeterministicAreaTargets(
                new[] { far, primary, near, primary }, primary, 20).ToList();

            Assert.Equal(new uint[] { 20, 21, 22 }, result.Select(unit => unit.ObjId));
        }

        [Fact]
        public void NativeTargetCapIsAppliedAfterPrimaryAndDistanceOrdering()
        {
            var primary = UnitAt(100, 0f, 0f);
            var candidates = new List<Unit> { primary };
            for (uint index = 1; index <= 25; index++)
                candidates.Add(UnitAt(100 + index, index, 0f));

            var result = PlotTargetInfo.TakeDeterministicAreaTargets(
                candidates.AsEnumerable().Reverse(), primary, 20).ToList();

            Assert.Equal(20, result.Count);
            Assert.Equal((uint)100, result[0].ObjId);
            Assert.DoesNotContain(result, unit => unit.ObjId > 119);
        }

        [Fact]
        public void NativeAoeConditionFiltersCandidatesInsteadOfBeingIgnored()
        {
            var caster = UnitAt(200, 0f, 0f);
            caster.Level = 15;
            var target = UnitAt(201, 1f, 0f);
            var state = new PlotState(caster, null, target, null, null, null);
            var condition = new PlotAoeCondition
            {
                Condition = new PlotCondition
                {
                    Kind = PlotConditionType.Level,
                    Param1 = 10,
                    Param2 = 20
                }
            };

            Assert.True(condition.CheckCondition(state, target));

            caster.Level = 9;
            Assert.False(condition.CheckCondition(state, target));
        }

        [Fact]
        public void ZeroRadiusSphereUsesEventSpecificAa8RadiusWithoutMutatingCatalog()
        {
            var catalogShape = new AreaShape
            {
                Id = 2876,
                Type = AreaShapeType.Sphere,
                Value1 = 0f
            };

            var resolved = PlotTargetAreaParams.ResolveShape(catalogShape, 3000);

            Assert.NotSame(catalogShape, resolved);
            Assert.Equal(0f, catalogShape.Value1);
            Assert.Equal(3f, resolved.Value1);
            Assert.Equal(catalogShape.Id, resolved.Id);
        }

        [Fact]
        public void RandomUnitSelectorUsesAa8ContractColumnsSevenThroughNine()
        {
            var template = new PlotEventTemplate
            {
                TargetUpdateMethodParam2 = 20,
                TargetUpdateMethodParam3 = 3000,
                TargetUpdateMethodParam4 = 90,
                TargetUpdateMethodParam7 = 1,
                TargetUpdateMethodParam8 = 4,
                TargetUpdateMethodParam9 = 127
            };

            var parameters = new PlotTargetRandomUnitParams(template);

            Assert.True(parameters.HitOnce);
            Assert.Equal((SkillTargetRelation)4, parameters.UnitRelationType);
            Assert.Equal((byte)127, parameters.UnitTypeFlag);
        }

        [Fact]
        public void ZeroVolumeRandomUnitShapeIsAPointSelector()
        {
            var parameters = new PlotTargetRandomUnitParams(new PlotEventTemplate())
            {
                Shape = new AreaShape
                {
                    Type = AreaShapeType.Sphere,
                    Value1 = 0f,
                    Value2 = 0f,
                    Value3 = 0f
                }
            };

            Assert.True(parameters.IsPointSelector);
        }

    }
}
