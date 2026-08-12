using System;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    public class AttackBuffTrigger : BuffTrigger
    {
        public override void Execute(object sender, EventArgs eventArgs)
        {
            var args = eventArgs as OnAttackArgs;
            _log.Trace(
                "Buff[{0}] {1} executed. Effect={2}",
                _buff.Template.BuffId,
                GetType().Name,
                Template.Effect?.Id ?? 0);

            if (!(_owner is Unit owner))
            {
                _log.Warn("AttackTrigger owner is not a Unit");
                return;
            }

            if (args?.Attacker == null || args.Target == null)
                return;

            if (Template.IsServerHitEffect)
            {
                ApplyServerHitEffect(args);
                return;
            }

            ApplyResolved(args.Attacker, args.Target, 0);
            if (_buff.Template.RemoveOnAttackBuffTrigger)
                owner.Buffs.TriggerRemoveOn(BuffRemoveOn.AttackBuffTrigger);
        }

        public static bool IsSuccessfulHit(
            OnAttackArgs args,
            int allowedDamageTypeMask,
            bool requirePositiveDamage)
        {
            return args != null
                && !args.IsTriggeredEffect
                && !args.IsPeriodicEffect
                && (!requirePositiveDamage || args.Amount > 0)
                && (allowedDamageTypeMask & (1 << (int)args.DamageType)) != 0;
        }

        private void ApplyServerHitEffect(OnAttackArgs args)
        {
            if (!IsSuccessfulHit(
                    args,
                    Template.AllowedDamageTypeMask,
                    Template.RequirePositiveDamage))
                return;

            // The AA8 coating target buffs are not dead-applicable. DamageEffect
            // raises OnAttack after applying HP, so a lethal weapon hit reaches
            // this consumer with an already-dead target and must not publish a
            // new impact buff into the completed death lifecycle.
            if (args.Target.Hp <= 0)
                return;

            var impactTemplate = SkillManager.Instance.GetBuffTemplate(Template.ServerImpactBuffId);
            if (impactTemplate == null)
            {
                _log.Error(
                    "AA8 server hit relation buff={0} references missing impact buff={1}",
                    _buff.Template.BuffId,
                    Template.ServerImpactBuffId);
                return;
            }

            args.Target.Buffs.AddBuff(new Buff(
                args.Target,
                args.Attacker,
                new SkillCasterUnit(args.Attacker.ObjId),
                impactTemplate,
                _buff.Skill,
                MechanicsRuntime.UtcNow));

            _log.Trace(
                "AA8ServerHitEffect sourceBuff={0} impactBuff={1} source={2} target={3}",
                _buff.Template.BuffId,
                Template.ServerImpactBuffId,
                args.Attacker.ObjId,
                args.Target.ObjId);
        }

        public AttackBuffTrigger(Buff owner, BuffTriggerTemplate template) : base(owner, template)
        {
        }
    }
}
