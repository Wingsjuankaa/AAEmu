using System;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Tasks.Skills;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class SetVariable : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.SetVariable;
        
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int value1,
            int value2,
            int value3,
            int value4)
        {
            // value1 is the destination (A..J), value2 is an offset and
            // value3 is the source operand (A..J, Zero or Targets).
            if (skill.ActivePlotState == null)
                _log.Error("No active plot state located.");
            else if (!PlotVariableOperations.TrySet(skill.ActivePlotState, value1, value2, value3))
                _log.Error("Invalid Plot Variable assignment: destination={0}, operand={1}.", value1, value3);

            _log.Trace("value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4);
        }
    }
}
