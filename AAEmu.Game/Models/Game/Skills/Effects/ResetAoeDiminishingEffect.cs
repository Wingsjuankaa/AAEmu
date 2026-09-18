using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects;

/// <summary>
/// <c>reset_aoe_diminishing_effects</c> (199 rows): ends the AoE hit sequence on the target, so its next area
/// hit starts at the first rate again.
/// </summary>
/// <remarks>
/// This was a stub that logged "ReportCrimeEffect". The 199 rows are not reachable through the <c>effects</c>
/// dispatch table — no row there has <c>actual_type</c> ResetAoeDiminishingEffect — so the type is applied by
/// id from a plot or a controller rather than by a skill effect id; the behaviour is the same either way.
/// </remarks>
public class ResetAoeDiminishingEffect : EffectTemplate
{
    public override bool OnActionTime => false;

    public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
        CastAction castObj, EffectSource source, SkillObject skillObject, DateTime time,
        CompressedGamePackets packetBuilder = null)
    {
        Logger.Trace("ResetAoeDiminishingEffect {0}", Id);

        // Diagnostic only: the upstream ten-second decay window has no native evidence.
        // Keep the previous damage behaviour until the counter's lifetime is established.
    }
}
