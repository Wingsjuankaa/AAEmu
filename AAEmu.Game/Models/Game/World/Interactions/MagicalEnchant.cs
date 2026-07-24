using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.World.Interactions
{
    public class MagicalEnchant : IWorldInteraction
    {
        public void Execute(
            Unit caster,
            SkillCaster casterType,
            BaseUnit target,
            SkillCastTarget targetType,
            uint skillId,
            uint itemId,
            DoodadFuncTemplate objectFunc)
        {
            if (caster is not Character character ||
                targetType is not SkillCastItemTarget itemTarget ||
                casterType is not SkillItem skillItem)
                return;

            var targetItem = character.Inventory.GetItemById(itemTarget.Id) as EquipItem;
            var reagent = character.Inventory.GetItemById(skillItem.ItemId);
            var validation = ItemSocketRuleService.Instance.Validate(targetItem, reagent);
            if (!validation.IsValid)
            {
                character.SendMessage("[Socket8] {0}", validation.Reason);
                if (targetItem != null && reagent != null)
                    character.SendPacket(new SCEnchantMagicalResultPacket(
                        false, targetItem.Id, reagent.TemplateId));
                return;
            }

            // AA8 no longer serializes the historical RuneId field in the
            // confirmed equipment detail layout. Installation remains gated
            // until the consolidated operation value and native persistence
            // slot are both confirmed.
            character.SendMessage(
                "[Socket8] Compatible enchanting gem; AA8 installation is pending protocol confirmation.");
            character.SendPacket(new SCEnchantMagicalResultPacket(
                false, targetItem.Id, reagent.TemplateId));
        }
    }
}
