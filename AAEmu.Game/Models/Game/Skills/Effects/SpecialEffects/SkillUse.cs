using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class SkillUse : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.SkillUse;
        
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int skillId,
            int delay,
            int chance,
            int value4)
        {
            // AA8/AA10 persist value4, but the supplied r575 x2game release,
            // dev and dedicate binaries expose no gameplay consumer for it.
            // Preserve it for evidence/logging; execution is defined by the
            // child id, delay, chance, trigger agents and child skill template.
            if (caster == null || skillId <= 0 || !PassesChance(chance, Rand.Next(0, 100)))
                return;

            var template = SkillManager.Instance.GetSkillTemplate((uint)skillId);
            if (template == null)
            {
                _log.Warn("SkillUse references missing skill template {0}", skillId);
                return;
            }

            var effectiveTarget = template.TargetType == SkillTargetType.Self ? caster : target;
            var effectiveTargetObj = BuildTarget(template.TargetType, effectiveTarget, targetObj);
            if (effectiveTarget == null || effectiveTargetObj == null)
            {
                _log.Warn("SkillUse could not resolve target for skill {0} targetType={1}",
                    skillId, template.TargetType);
                return;
            }

            var useSkill = new Skill(template, caster);
            caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.UseSkill);//Not sure if it belongs here.
            TaskManager.Instance.Schedule(
                new UseSkillTask(useSkill, caster, casterObj, effectiveTarget, effectiveTargetObj, skillObject),
                TimeSpan.FromMilliseconds(Math.Max(0, delay)));
            _log.Trace("SkillId {0}, Delay {1}, Chance {2}, value4 {3}", skillId, delay, chance, value4);
        }

        public static bool PassesChance(int chance, int roll)
        {
            return chance <= 0 || chance >= 100 || roll < chance;
        }

        public static SkillCastTarget BuildTarget(
            SkillTargetType targetType,
            BaseUnit target,
            SkillCastTarget inheritedTarget)
        {
            if (target == null)
                return null;

            switch (targetType)
            {
                case SkillTargetType.Pos:
                case SkillTargetType.BallisticPos:
                case SkillTargetType.SummonPos:
                case SkillTargetType.RelativePos:
                case SkillTargetType.SourcePos:
                case SkillTargetType.ArtilleryPos:
                case SkillTargetType.CursorPos:
                    var position = target.Transform.World.Position;
                    return new SkillCastPositionTarget
                    {
                        Type = SkillCastTargetType.Position,
                        PosX = position.X,
                        PosY = position.Y,
                        PosZ = position.Z,
                        PosRot = target.Transform.World.ToRollPitchYawDegrees().Z
                    };
                case SkillTargetType.Doodad when target is Doodad:
                    return new SkillCastDoodadTarget
                    {
                        Type = SkillCastTargetType.Doodad,
                        ObjId = target.ObjId
                    };
                default:
                    return new SkillCastUnitTarget(target.ObjId)
                    {
                        Type = SkillCastTargetType.Unit
                    };
            }
        }
    }
}
