using System;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// Native 8.0 combat-resource descriptor.
    /// </summary>
    /// <remarks>
    /// The compact layout is confirmed in x2game.dll FUN_39974c30. The 3.0
    /// backend does not yet expose the corresponding per-unit resource state,
    /// so execution remains intentionally inert instead of assigning guessed
    /// semantics to the resource id.
    /// </remarks>
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
            _log.Warn(
                "CombatResourceEffect {0} is data-complete but runtime resource {1} is not implemented",
                Id,
                CombatResourceId);
        }
    }
}
