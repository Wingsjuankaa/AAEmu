using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
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

            if (validation.Definition.Kind != ItemSocketDefinitionKind.EnchantingGem)
            {
                character.SendMessage(
                    "[Socket8] The selected reagent is not an AA8 enchanting gem.");
                character.SendPacket(new SCEnchantMagicalResultPacket(
                    false, targetItem.Id, reagent.TemplateId));
                return;
            }

            // x2game.dll exposes equipment detail +0x08 as gemInfo. This is
            // the AA8 successor of the historical standalone rune field.
            targetItem.EnchantingGemItemId = reagent.TemplateId;
            character.SendPacket(
                new SCItemTaskSuccessPacket(
                    ItemTaskType.EnchantMagical,
                    new ItemUpdate(targetItem),
                    new System.Collections.Generic.List<ulong>()));

            if (targetItem.SlotType == SlotType.Equipment)
            {
                character.UpdateGearBonuses(null, null);
                EquipmentSyncService.Instance.Resync(character);
            }

            character.SendPacket(new SCEnchantMagicalResultPacket(
                true, targetItem.Id, reagent.TemplateId));
        }
    }
}
