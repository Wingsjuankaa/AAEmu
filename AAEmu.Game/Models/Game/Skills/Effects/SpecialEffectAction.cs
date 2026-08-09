using System;
using AAEmu.Game.Models.Game.Units;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public abstract class SpecialEffectAction
    {
        protected static Logger _log = LogManager.GetCurrentClassLogger();
        protected virtual SpecialType SpecialEffectActionType { get; set; }

        public abstract void Execute(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj, Skill skill, SkillObject skillObject, DateTime time, int value1, int value2, int value3, int value4);

        public virtual void Execute(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj, Skill skill, SkillObject skillObject, DateTime time, int value1, int value2, int value3,
            int value4, int value5, int value6, int value7)
        {
            Execute(caster, casterObj, target, targetObj, castObj, skill, skillObject, time,
                value1, value2, value3, value4);
        }
    }
} 
