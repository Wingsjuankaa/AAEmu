using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class ItemCapScale : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ItemCapScale;

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
                casterObj is not SkillItem ||
                targetObj is not SkillCastItemTarget targetItem)
                return;

            var equipment = owner.Inventory.GetItemById(targetItem.Id) as EquipItem;
            var service = ItemEnchantScaleService.Instance;
            if (!service.CanTemper(equipment))
            {
                owner.SendMessage("[Temper8] This item is not eligible for native AA8 temper.");
                return;
            }

            var current = service.Get(equipment.ScaledA);
            var nextId = (ushort)(equipment.ScaledA + 1);
            var next = service.Get(nextId);
            if (next == null || nextId > equipment.Template.MaxEnchantScaleId)
            {
                owner.SendMessage("[Temper8] The item is already at its AA8 temper cap.");
                return;
            }

            // Replaces the historical random ScaleMin/ScaleMax implementation.
            // The AA8 outcome ratios are known, but reagent/currency consumption
            // and the outcome packet are still being provenance-locked.
            owner.SendMessage(
                "[Temper8] {0} -> {1}: success={2}/10000, great={3}/10000, down={4}/10000. Execution is gated.",
                current?.Name ?? "+0",
                next.Name,
                next.SuccessRatio,
                next.GreatSuccessRatio,
                next.DownRatio);
        }
    }
}
