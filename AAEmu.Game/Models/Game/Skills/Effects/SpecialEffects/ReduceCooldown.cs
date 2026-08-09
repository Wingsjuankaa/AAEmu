using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    /// <summary>
    /// Native AA8 special-effect type 153. value1 selects a skill, value2 a
    /// cooldown tag, value6 is the flat millisecond delta and value7 percent.
    /// </summary>
    public class ReduceCooldown : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ReduceCooldown;

        public override void Execute(
            Unit caster,
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
            Execute(caster, casterObj, target, targetObj, castObj, skill, skillObject, time,
                value1, value2, value3, value4, 0, 0, 0);
        }

        public override void Execute(
            Unit caster,
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
            int value4,
            int value5,
            int value6,
            int value7)
        {
            if (!(caster is Character character))
                return;

            var selector = value1 != 0
                ? CooldownSelector.Skill((uint)value1)
                : CooldownSelector.Tag((uint)value2);
            if (selector.Id == 0)
                return;

            character.ReduceSkillCooldown(
                selector,
                Math.Max(0, value6),
                Math.Max(0, value7),
                value3 != 0,
                value4 != 0,
                value5 != 0);
        }
    }
}
