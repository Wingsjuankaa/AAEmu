using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ManaCost : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ManaCost;
        
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

            if (caster is Character character && skill?.Template != null)
            {
                // AA8 plot descriptors encode the same two components used by
                // skills: value1 == mana_cost and value2 == mana_level_md * 100.
                // Use the native skill-rank/ability-level calculation instead of
                // the old empirical value2 / 6.35 approximation.
                var manaCost = skill.CalculateManaCost(character, value1, value2 / 100d);
                character.ReduceCurrentMp(null, manaCost);
                
                character.LastCast = DateTime.UtcNow;
                character.IsInPostCast = true;
                // TODO / 10
            }
        }
    }
}
