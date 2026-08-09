using System;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    public class BuffTrigger
    {
        public enum AgentId : uint
        {
            Owner = 0,
            EventSource = 1,
            EventTarget = 2,
            OriginalSource = 3
        }

        protected static Logger _log = LogManager.GetCurrentClassLogger();
        protected Buff _buff;
        protected readonly BaseUnit _owner;
        public BuffTriggerTemplate Template { get; set; }
        public virtual void Execute(object sender, EventArgs eventArgs)
        {
            _log.Trace("Buff[{0}] {1} executed. Applying {2}[{3}]!", _buff?.Template?.BuffId, this.GetType().Name, Template.Effect.GetType().Name, Template.Effect.Id);

            if (!(_owner is Unit owner))
            {
                _log.Warn("Owner is not a Unit");
                return;
            }

            ApplyResolved(owner, owner, 0);
        }

        public BuffTrigger(Buff buff, BuffTriggerTemplate template)
        {
            _buff = buff;
            _owner = _buff.Owner;
            Template = template;
        }

        protected void ApplyResolved(Unit eventSource, Unit eventTarget, int amount)
        {
            if (!(_owner is Unit owner))
                return;

            var source = ResolveAgent(
                Template.SourceAgentId,
                owner,
                eventSource,
                eventTarget,
                _buff.Caster);
            var target = ResolveAgent(
                Template.TargetAgentId,
                owner,
                eventSource,
                eventTarget,
                _buff.Caster);
            if (source == null || target == null)
            {
                _log.Warn(
                    "AA8BuffTrigger unresolved agents trigger={0} buff={1} sourceAgent={2} targetAgent={3}",
                    Template.Id,
                    _buff.Template.BuffId,
                    Template.SourceAgentId,
                    Template.TargetAgentId);
                return;
            }

            if (Template.OwnerBuffTagId != 0
                && !owner.Buffs.CheckBuffTag(Template.OwnerBuffTagId))
                return;
            if (Template.OwnerNoBuffTagId != 0
                && owner.Buffs.CheckBuffTag(Template.OwnerNoBuffTagId))
                return;
            if (Template.SourceBuffTagId != 0
                && !source.Buffs.CheckBuffTag(Template.SourceBuffTagId))
                return;
            if (Template.SourceNoBuffTagId != 0
                && source.Buffs.CheckBuffTag(Template.SourceNoBuffTagId))
                return;
            if (Template.TargetBuffTagId != 0
                && !target.Buffs.CheckBuffTag(Template.TargetBuffTagId))
                return;
            if (Template.TargetNoBuffTagId != 0
                && target.Buffs.CheckBuffTag(Template.TargetNoBuffTagId))
                return;

            _log.Trace(
                "AA8BuffTrigger id={0} buff={1} source={2} target={3} effect={4} sourceAgent={5} targetAgent={6}",
                Template.Id,
                _buff.Template.BuffId,
                source.ObjId,
                target.ObjId,
                Template.Effect.Id,
                Template.SourceAgentId,
                Template.TargetAgentId);
            Template.Effect.Apply(
                source,
                new SkillCasterUnit(source.ObjId),
                target,
                new SkillCastUnitTarget(target.ObjId),
                new CastBuff(_buff),
                new EffectSource(_buff.Skill, _buff.Template)
                {
                    Amount = amount,
                    IsTrigger = true
                },
                null,
                DateTime.UtcNow);
        }

        public static Unit ResolveAgent(
            uint agentId,
            Unit owner,
            Unit eventSource,
            Unit eventTarget,
            Unit originalSource)
        {
            switch ((AgentId)agentId)
            {
                case AgentId.Owner:
                    return owner;
                case AgentId.EventSource:
                    return eventSource;
                case AgentId.EventTarget:
                    return eventTarget;
                case AgentId.OriginalSource:
                    return originalSource;
                default:
                    return null;
            }
        }
    }
}
