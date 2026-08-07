using System;

using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class Combo : SpecialEffectAction
    {
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int comboSkillId,
            int timeFromNow,
            int value3,
            int value4)
        {
            // AA8 x2game.dll FUN_39899660 walks the current skill's effects,
            // finds SpecialEffect type 48 (Combo), and recursively selects the
            // next skill id on the client. Holding the action key therefore
            // sends 10752 -> 24894 -> 24895 as three ordinary skill requests.
            //
            // The 2026-08-05 live trace confirms that exact client-driven
            // sequence. Scheduling the child here would create a second,
            // server-generated cast and duplicate damage/mana consumption if
            // this descriptor is ever reached by a non-plot path.
            _log.Trace(
                "Client-driven Combo transition nextSkill={0}, windowMs={1}, value3={2}, value4={3}",
                comboSkillId,
                timeFromNow,
                value3,
                value4);
        }
    }
}
