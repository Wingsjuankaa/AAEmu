using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

internal sealed record MechanicsSandboxBuffSnapshot(uint TemplateId, Unit Caster, SkillCaster SkillCaster,
    int EffectiveDuration, int Stack, int Charge, bool Passive, uint AbLevel, bool ZoneAuthored)
{
    public static MechanicsSandboxBuffSnapshot Capture(Buff buff) => new(buff.Template.Id, buff.Caster,
        buff.SkillCaster, buff.Duration, buff.Stack, buff.Charge, buff.Passive, buff.AbLevel, buff.ZoneAuthored);

    public Buff Create(Unit owner, BuffTemplate template)
    {
        if (ZoneAuthored)
            throw new InvalidOperationException("El baseline contiene un buff administrado por Zone; no se puede promover a World.");
        return new Buff(owner, Caster ?? owner, SkillCaster ?? new SkillCasterUnit(owner.ObjId), template, null,
            DateTime.MinValue)
        {
            Stack = Stack, Charge = Charge, Passive = Passive, AbLevel = AbLevel, ZoneAuthored = ZoneAuthored
        };
    }
}
