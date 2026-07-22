using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Plots
{
    public class PlotAoeCondition
    {
        public PlotCondition Condition { get; set; }
        public int Position { get; set; }

        public bool CheckCondition(PlotState state, BaseUnit target)
        {
            if (Condition == null || state?.Caster == null || target == null)
                return false;

            return Condition.Check(
                state.Caster,
                state.CasterCaster,
                target,
                state.TargetCaster,
                state.SkillObject,
                null,
                state.ActiveSkill);
        }
    }
}
