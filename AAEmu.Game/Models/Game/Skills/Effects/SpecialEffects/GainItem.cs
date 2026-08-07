using System;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class GainItem : SpecialEffectAction
    {
        public override void Execute(Unit caster,
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
            if (!(caster is Character character))
                return;

            if (value1 <= 0)
            {
                _log.Warn("Special effects: GainItem ignored invalid item template id {0}", value1);
                return;
            }

            var itemId = (uint)value1;
            var itemCount = value2 > 0 ? value2 : 1;
            var acquired = character.Inventory.TryAddNewItem(
                ItemTaskType.SkillEffectGainItem,
                itemId,
                itemCount,
                0);

            if (!acquired)
            {
                _log.Warn(
                    "Special effects: GainItem failed to give item {0} x{1} to character {2}",
                    itemId,
                    itemCount,
                    character.Id);
            }
        }
    }
}
