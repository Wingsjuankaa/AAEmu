using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>AA10 special effect 177: awards its authored value to the active zone competition.</summary>
public sealed class GiveFactionCompetitionPoint : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.GiveFactionCompetitionPoint;

    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
        SkillCastTarget targetObj, CastAction castObj, Skill skill, SkillObject skillObject,
        DateTime time, int value1, int value2, int value3, int value4)
    {
        var actor = caster?.GetOwnerCharacter() ?? caster;
        if (actor != null && value1 > 0)
            WorldIntegration.GiveFactionCompetitionPoint?.Invoke(actor, (uint)value1);
    }
}
