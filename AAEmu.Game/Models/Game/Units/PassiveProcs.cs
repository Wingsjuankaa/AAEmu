using System;
using System.Collections.Generic;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using NLog;

namespace AAEmu.Game.Models.Game.Units
{
    public class PassiveProcs
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly object _lock = new object();
        private readonly BaseUnit _owner;
        private readonly List<PassiveProcTemplate> _templates = new List<PassiveProcTemplate>();
        private readonly Dictionary<uint, DateTime> _availableAt = new Dictionary<uint, DateTime>();

        public PassiveProcs(BaseUnit owner)
        {
            _owner = owner;
        }

        public void Add(uint reqBuffId)
        {
            lock (_lock)
            {
                foreach (var template in SkillManager.Instance.GetPassiveProcs(reqBuffId))
                {
                    if (!_templates.Contains(template))
                        _templates.Add(template);
                }
            }
        }

        public void Remove(uint reqBuffId)
        {
            lock (_lock)
            {
                foreach (var template in SkillManager.Instance.GetPassiveProcs(reqBuffId))
                {
                    _templates.Remove(template);
                    _availableAt.Remove(template.Id);
                }
            }
        }

        public void TriggerDamageSkillHit(Unit caster, Skill skill, DateTime time)
        {
            if (caster == null || skill == null || _owner != caster)
                return;

            var tags = SkillManager.Instance.GetSkillTags(skill.Template.Id);
            List<PassiveProcTemplate> triggered;
            lock (_lock)
            {
                triggered = new List<PassiveProcTemplate>();
                foreach (var template in _templates)
                {
                    if (!template.Matches(PassiveProcTriggerKind.DamageSkillHit, tags))
                        continue;
                    if (_availableAt.TryGetValue(template.Id, out var availableAt) && time < availableAt)
                        continue;

                    _availableAt[template.Id] = time.AddMilliseconds(template.CooldownMs);
                    triggered.Add(template);
                }
            }

            foreach (var template in triggered)
                Apply(template, caster, skill, time);
        }

        private static void Apply(PassiveProcTemplate template, Unit caster, Skill skill, DateTime time)
        {
            var effect = SkillManager.Instance.GetEffectTemplate(template.EffectId);
            if (effect == null)
            {
                Log.Error(
                    "AA8 passive proc {0} cannot apply missing effect {1}",
                    template.Id,
                    template.EffectId);
                return;
            }

            Log.Debug(
                "AA8PassiveProc id={0} owner={1} reqBuff={2} skill={3} tag={4} effect={5} cooldownMs={6}",
                template.Id,
                caster.ObjId,
                template.ReqBuffId,
                skill.Template.Id,
                template.SkillTagId,
                template.EffectId,
                template.CooldownMs);
            var casterObj = new SkillCasterUnit(caster.ObjId);
            effect.Apply(
                caster,
                casterObj,
                caster,
                new SkillCastUnitTarget(caster.ObjId),
                new CastSkill(skill.Template.Id, skill.TlId),
                new EffectSource(skill),
                null,
                time);
        }
    }
}
