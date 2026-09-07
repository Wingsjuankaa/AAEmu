using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public sealed class EquipSlotReinforceAddExp : SpecialEffectAction
{
    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
        SkillCastTarget targetObj, CastAction castObj, Skill skill, SkillObject skillObject,
        DateTime time, int value1, int value2, int value3, int value4)
    {
        if (caster is Character character && skillObject is SkillObjectEquipSlotReinforceMaterials context)
        {
            if (context.BatchRequest is { } batch)
                character.EquipSlotReinforce?.CompleteBatch(batch, skill);
            else
                character.EquipSlotReinforce?.AddExperience(context.EquipSlot, context.MaterialId, context.AutoUseAaPoint);
        }
    }
}
