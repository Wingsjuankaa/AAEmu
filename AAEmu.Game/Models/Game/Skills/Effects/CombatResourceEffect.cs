using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>Native AA8 combat-resource mutation.</summary>
    public class CombatResourceEffect : EffectTemplate
    {
        public int Chance { get; set; }
        public uint CombatResourceId { get; set; }
        public int MaxCombatResource { get; set; }
        public int MinCombatResource { get; set; }
        public bool ResetRemainTime { get; set; }

        public override bool OnActionTime => false;

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source,
            SkillObject skillObject, DateTime time,
            CompressedGamePackets packetBuilder = null)
        {
            if (!(target is Unit targetUnit))
                return;

            // Zero in this descriptor family means unconditional. Positive
            // values are percentages.
            if (Chance > 0 && Rand.Next(1, 101) > Chance)
                return;

            var resourceId = CombatResourceId;
            if (resourceId == 0 && source?.Skill?.Template != null)
                resourceId = CombatResourceGameData.Instance.ResolvePrimaryResourceId(
                    (AbilityType)source.Skill.Template.AbilityId);
            if (resourceId == 0)
                return;

            var minimum = Math.Min(MinCombatResource, MaxCombatResource);
            var maximum = Math.Max(MinCombatResource, MaxCombatResource);
            var amount = minimum == maximum ? minimum : Rand.Next(minimum, maximum + 1);
            targetUnit.AddCombatResource(resourceId, amount, ResetRemainTime);
        }
    }
}
