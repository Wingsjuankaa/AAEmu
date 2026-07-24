using System.Collections.Generic;
using System.Linq;

namespace AAEmu.Game.Models.Game.Skills.Buffs
{
    public enum PassiveProcTriggerKind
    {
        DamageSkillHit = 1
    }

    public class PassiveProcTemplate
    {
        public uint Id { get; set; }
        public uint ReqBuffId { get; set; }
        public PassiveProcTriggerKind TriggerKind { get; set; }
        public uint SkillTagId { get; set; }
        public uint EffectId { get; set; }
        public int CooldownMs { get; set; }

        public bool Matches(PassiveProcTriggerKind triggerKind, IReadOnlyCollection<uint> skillTags)
        {
            return TriggerKind == triggerKind
                   && (SkillTagId == 0 || skillTags.Contains(SkillTagId));
        }
    }
}
