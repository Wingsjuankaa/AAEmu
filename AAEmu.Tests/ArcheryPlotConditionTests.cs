using System;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class ArcheryPlotConditionTests
    {
        [Fact]
        public void CastingUseableConditionReadsReleasedPlotPercentage()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 36470 });
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent { Id = 24216, Casting = true, CastingUseable = true };
            var started = new DateTime(2026, 8, 7, 0, 0, 0, DateTimeKind.Utc);
            state.BeginCasting(edge, 4000, started);
            Assert.True(state.TryReleaseCastingUseable(started.AddMilliseconds(3000)));
            caster.ActivePlotState = state;

            var selectedBand = new PlotCondition
            {
                Kind = PlotConditionType.CastingUseable,
                Param1 = 75,
                Param2 = 99
            };
            var rejectedBand = new PlotCondition
            {
                Kind = PlotConditionType.CastingUseable,
                Param1 = 50,
                Param2 = 74
            };

            Assert.True(selectedBand.Check(caster, null, null, null, null, null, skill));
            Assert.False(rejectedBand.Check(caster, null, null, null, null, null, skill));
        }

        [Fact]
        public void PlotConditionUnitRequirementUsesExactAa8TargetHealthContract()
        {
            var condition = new PlotCondition
            {
                Kind = PlotConditionType.UnitReqs,
                OrUnitReqs = false
            };
            condition.UnitRequirements.Add(new SkillUnitRequirement
            {
                OwnerId = 14753,
                KindId = SkillUnitRequirement.TargetHealthLessThanKind,
                Value1 = 1,
                Value2 = 30
            });
            var target = new Unit { Hp = 299, MaxHp = 1000 };

            Assert.True(condition.Check(null, null, target, null, null, null, null));
            target.Hp = 300;
            Assert.False(condition.Check(null, null, target, null, null, null, null));
        }
    }
}
