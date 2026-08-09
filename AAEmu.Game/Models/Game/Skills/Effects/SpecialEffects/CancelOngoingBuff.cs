using System;

using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class CancelOngoingBuff : SpecialEffectAction
    {
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
            _log.Trace("value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4);

            // The AA8 plot places this marker at the start of plot-only skills.
            // Skill.Use has already applied the descriptor contract before the
            // plot starts (cancel_ongoing_buffs plus its exception tag), so doing
            // it again here would fire remove-on-start triggers twice.
        }
    }
}
