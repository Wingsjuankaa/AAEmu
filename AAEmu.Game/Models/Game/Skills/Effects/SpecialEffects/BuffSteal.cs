using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class BuffSteal : SpecialEffectAction
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
            if (!(target is Unit targetUnit) || caster == null)
                return;

            // AA8 has both descriptor generations in the same compact:
            // legacy rows use value1, current Shadowplay rows use value3.
            var count = ResolveCount(value1, value3);
            var requiredTagId = value4 > 0 ? (uint)value4 : 0u;
            var transferred = targetUnit.Buffs.StealGoodBuffs(
                caster,
                count,
                requiredTagId,
                time);

            _log.Trace(
                "Special effects: BuffSteal caster={0}, target={1}, count={2}, tag={3}, transferred={4}",
                caster.ObjId,
                targetUnit.ObjId,
                count,
                requiredTagId,
                transferred);
        }

        public static int ResolveCount(int value1, int value3) =>
            value3 > 0 ? value3 : Math.Max(0, value1);
    }
}
