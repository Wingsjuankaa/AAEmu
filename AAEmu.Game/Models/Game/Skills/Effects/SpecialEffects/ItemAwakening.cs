using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    /// <summary>
    /// Native AA8 awakening entry point. The directed reactive/mapping graph
    /// is loaded, but mutation remains fail-closed until the result packet,
    /// probability scale and crystallization state are confirmed.
    /// </summary>
    public class ItemAwakening : SpecialEffectAction
    {
        public override void Execute(
            Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int value1,
            int value2,
            int value3,
            int value4)
        {
            if (caster is Character owner)
            {
                owner.SendMessage(
                    "[Evolution8] Awakening group {0} is recognized, but mutation is isolated until its native AA8 result protocol is complete.",
                    value1);
            }
            if (skill != null)
            {
                skill.Cancelled = true;
                caster.BroadcastPacket(
                    new Core.Packets.G2C.SCSkillEndedPacket(),
                    true);
            }
        }
    }
}
