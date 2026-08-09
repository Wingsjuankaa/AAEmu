using System;

using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class Cooldown : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.Cooldown;
        
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int cooldownTime,
            int value2,
            int value3,
            int value4)
        {
            if (caster == null || skill?.Template == null || cooldownTime < 0)
                return;

            // AA8 skill_modifiers contains Cooldown rows for Battlerage and
            // other specializations.  The plot value is the unmodified base
            // duration; applying the shared modifier cache here keeps plot-
            // driven cooldowns on the same path as ordinary skill cooldowns.
            var effectiveCooldown = caster.ApplySkillModifiers(
                skill,
                SkillAttribute.Cooldown,
                cooldownTime);
            caster.Cooldowns.StartCooldown(
                skill.Template.Id,
                (uint)Math.Max(0d, effectiveCooldown),
                skill.TlId);
            _log.Trace("cooldownTime {0}, value2 {1}, value3 {2}, value4 {3}", cooldownTime, value2, value3, value4);
        }
    }
}
