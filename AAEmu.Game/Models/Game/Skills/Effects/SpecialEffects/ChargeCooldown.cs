using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    /// <summary>
    /// Marks the native AA8 recharge interval for a multi-charge skill.
    /// </summary>
    /// <remarks>
    /// The AA8 client consumes SpecialEffect 158 from the plot and updates its
    /// own charge-cooldown lane. The server currently treats ordinary skill
    /// cooldowns as client-authoritative as well: UnitCooldowns records them,
    /// but Skill.Use does not reject a request from that cache. Consequently
    /// this action must preserve the descriptor without inventing a second
    /// packet or an independent rejection policy. Loading ChargeCount and
    /// ChargeCooldownTime on SkillTemplate retains the authoritative contract
    /// for a future server-authoritative cooldown pass.
    /// </remarks>
    public class ChargeCooldown : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ChargeCooldown;

        public override void Execute(
            Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int cooldownTime,
            int value2,
            int value3,
            int value4)
        {
            _log.Trace(
                "AA8 ChargeCooldown skill={0} duration={1} configuredDuration={2} chargeCount={3}",
                skill?.Template?.Id ?? 0,
                cooldownTime,
                skill?.Template?.ChargeCooldownTime ?? 0,
                skill?.Template?.ChargeCount ?? 0);
        }
    }
}
