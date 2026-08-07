using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class DisturbCasting : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.DisturbCasting;
        
        // Parameters are estimated to be :
        // value1 = chance ?
        // value2 = delay ?
        public override void Execute(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj, CastAction castObj,
            Skill skill, SkillObject skillObject, DateTime time, int chance, int delay, int value3, int value4)
        {
            if (!(target is Unit unit) || !PassesChance(chance, Rand.Next(0, 100)))
                return;

            if (delay <= 0)
                unit.InterruptSkills();
            else
                TaskManager.Instance.Schedule(
                    new InterruptSkillTask(unit),
                    TimeSpan.FromMilliseconds(delay));
        }

        public static bool PassesChance(int chance, int roll) =>
            chance <= 0 || chance >= 100 || roll < chance;
    }
}
