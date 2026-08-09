using System.Collections.Generic;
using System.Linq;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Units;
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
    }
}
