using System.Collections.Generic;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public enum EquipmentValidationFailure
    {
        None,
        InvalidSlot,
        InvalidItemType,
        InventoryFull,
        TwoHandConflict,
        RequirementNotMet
    }

    public sealed class EquipmentTransitionPlan
    {
        public EquipmentValidationFailure Failure { get; set; }
        public string Reason { get; set; } = string.Empty;
        public List<Item> MoveToBag { get; } = new List<Item>();
        public bool IsValid => Failure == EquipmentValidationFailure.None;
    }

    public interface IEquipmentRuleService
    {
        bool IsTwoHanded(Item item);
        bool CanOccupyPhysicalSlot(Item item, EquipmentItemSlot slot);
        EquipmentTransitionPlan Plan(Character owner, Item incoming, EquipmentItemSlot destination);
    }

    public sealed class EquipmentRuleService : IEquipmentRuleService
    {
        public static EquipmentRuleService Instance { get; } = new EquipmentRuleService();

        public bool IsTwoHanded(Item item)
        {
            return item?.Template is WeaponTemplate weapon &&
                   (EquipmentItemSlotType)weapon.HoldableTemplate.SlotTypeId ==
                   EquipmentItemSlotType.TwoHanded;
        }

        public bool CanOccupyPhysicalSlot(Item item, EquipmentItemSlot slot)
        {
            if (item?.Template is BackpackTemplate)
                return slot == EquipmentItemSlot.Backpack;
            if (item?.Template is BodyPartTemplate bodyPart)
                return bodyPart.SlotTypeId >= (uint)EquipmentItemSlotType.Face &&
                       (byte)slot == bodyPart.SlotTypeId - 4;
            if (!(item is EquipItem))
                return false;

            if (item.Template is WeaponTemplate weapon)
            {
                var type = (EquipmentItemSlotType)weapon.HoldableTemplate.SlotTypeId;
                switch (type)
                {
                    case EquipmentItemSlotType.TwoHanded:
                    case EquipmentItemSlotType.Mainhand:
                        return slot == EquipmentItemSlot.Mainhand;
                    case EquipmentItemSlotType.Offhand:
                    case EquipmentItemSlotType.Shield:
                        return slot == EquipmentItemSlot.Offhand;
                    case EquipmentItemSlotType.OneHanded:
                        return slot == EquipmentItemSlot.Mainhand || slot == EquipmentItemSlot.Offhand;
                    case EquipmentItemSlotType.Ranged:
                        return slot == EquipmentItemSlot.Ranged;
                    case EquipmentItemSlotType.Instrument:
                        return slot == EquipmentItemSlot.Musical;
                    default:
                        return false;
                }
            }

            if (item.Template is ArmorTemplate armor)
                return (byte)slot == armor.SlotTemplate.SlotTypeId - 1;
            if (item.Template is AccessoryTemplate accessory)
            {
                var type = (EquipmentItemSlotType)accessory.SlotTemplate.SlotTypeId;
                if (type == EquipmentItemSlotType.Ear)
                    return slot == EquipmentItemSlot.Ear1 || slot == EquipmentItemSlot.Ear2;
                if (type == EquipmentItemSlotType.Finger)
                    return slot == EquipmentItemSlot.Finger1 || slot == EquipmentItemSlot.Finger2;
                return (byte)slot == accessory.SlotTemplate.SlotTypeId - 1;
            }

            return true;
        }

        public EquipmentTransitionPlan Plan(Character owner, Item incoming, EquipmentItemSlot destination)
        {
            var result = new EquipmentTransitionPlan();
            if (owner == null || incoming == null || !CanOccupyPhysicalSlot(incoming, destination))
            {
                result.Failure = EquipmentValidationFailure.InvalidSlot;
                result.Reason = "The AA8 item definition does not allow that physical slot.";
                return result;
            }

            if (incoming.Template.LevelRequirement > 0 &&
                owner.Level < incoming.Template.LevelRequirement)
            {
                result.Failure = EquipmentValidationFailure.RequirementNotMet;
                result.Reason =
                    $"Requires level {incoming.Template.LevelRequirement}; owner level is {owner.Level}.";
                return result;
            }

            var main = owner.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Mainhand);
            var off = owner.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Offhand);
            if (IsTwoHanded(incoming) && off != null)
                result.MoveToBag.Add(off);
            else if (destination == EquipmentItemSlot.Offhand && IsTwoHanded(main))
                result.MoveToBag.Add(main);

            if (owner.Inventory.Bag.FreeSlotCount < result.MoveToBag.Count)
            {
                result.Failure = EquipmentValidationFailure.InventoryFull;
                result.Reason = "No inventory room for the hand displaced by this transition.";
            }

            return result;
        }
    }
}
