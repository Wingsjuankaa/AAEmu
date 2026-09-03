using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Core.Managers;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class GainGachaLootPackItem : SpecialEffectAction
{
    public override void Execute(BaseUnit caster,
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
        // The ordinary use cast opens the native client window. Execute is a second CSStartSkill
        // carrying type-16 options plus the exact source and consume-item slots.
        if (caster is not Character character ||
            skillObject is not SkillObjectGachaRollOptions options)
            return;

        LootGachaService.Instance.Execute(
            character,
            casterObj as SkillItem,
            targetObj as SkillCastItemTarget,
            options.Count);
    }
}
