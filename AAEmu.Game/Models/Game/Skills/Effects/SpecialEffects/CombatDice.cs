using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class CombatDice : SpecialEffectAction
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
            if (skill == null || !(target is Unit targetUnit))
                return;

            // AA8 uses this plot primitive to materialize one combat-dice
            // result before subsequent kind-9 conditions branch on it. Damage
            // effects and conditions reuse the same per-target result.
            if (!skill.HitTypes.ContainsKey(targetUnit.ObjId))
                skill.HitTypes[targetUnit.ObjId] = skill.RollCombatDice(caster, targetUnit);

            _log.Trace(
                "Special effects: CombatDice skill={0} target={1} result={2}",
                skill.Template?.Id,
                targetUnit.ObjId,
                skill.HitTypes[targetUnit.ObjId]);
        }
    }
}
