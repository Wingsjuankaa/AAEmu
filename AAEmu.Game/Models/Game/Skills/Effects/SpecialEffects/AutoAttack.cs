using System;

using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class AutoAttack : SpecialEffectAction
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

            // AA8 Sorcery plots use value1=0 on skills whose descriptor has
            // start_autoattack=true. That flag means hold-to-repeat this spell;
            // it must not start weapon skill 2/4 after the spell lands.
            if (skill?.Template?.StartAutoAttack == true)
                return;

            _log.Debug(
                "AutoAttack special for skill {0} requires the generic weapon auto-attack runtime",
                skill?.Template?.Id ?? 0);
        }
    }
}
