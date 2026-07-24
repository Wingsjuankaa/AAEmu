using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemCapScaleReset : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ItemCapScaleReset;

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
            if (caster is not Character owner ||
                targetObj is not SkillCastItemTarget targetItem)
                return;

            var equipment = owner.Inventory.GetItemById(targetItem.Id) as EquipItem;
            if (!ItemEnchantScaleService.Instance.CanTemper(equipment))
            {
                owner.SendMessage("[Temper8] This item has no native AA8 temper state.");
                return;
            }

            owner.SendMessage(
                "[Temper8] Reset of {0} is gated until AA8 reagent consumption and result protocol are confirmed.",
                ItemEnchantScaleService.Instance.Get(equipment.ScaledA)?.Name ?? "+0");
        }
    }
}
