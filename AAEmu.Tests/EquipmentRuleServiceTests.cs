using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Tests.Utils.Mocks;

using Xunit;

namespace AAEmu.Tests
{
    public class EquipmentRuleServiceTests
    {
        [Fact]
        public void TwoHandedWeaponCanOnlyOccupyMainHand()
        {
            var weapon = new Weapon
            {
                Template = new WeaponTemplate
                {
                    HoldableTemplate = new Holdable
                    {
                        SlotTypeId = (uint)EquipmentItemSlotType.TwoHanded
                    }
                }
            };

            Assert.True(EquipmentRuleService.Instance.IsTwoHanded(weapon));
            Assert.True(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(weapon, EquipmentItemSlot.Mainhand));
            Assert.False(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(weapon, EquipmentItemSlot.Offhand));
        }

        [Fact]
        public void OneHandedWeaponCanOccupyEitherHand()
        {
            var weapon = new Weapon
            {
                Template = new WeaponTemplate
                {
                    HoldableTemplate = new Holdable
                    {
                        SlotTypeId = (uint)EquipmentItemSlotType.OneHanded
                    }
                }
            };

            Assert.True(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(weapon, EquipmentItemSlot.Mainhand));
            Assert.True(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(weapon, EquipmentItemSlot.Offhand));
        }

        [Fact]
        public void BackpackUsesItsDedicatedPhysicalSlot()
        {
            var backpack = new Backpack { Template = new BackpackTemplate() };

            Assert.True(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(backpack, EquipmentItemSlot.Backpack));
            Assert.False(EquipmentRuleService.Instance.CanOccupyPhysicalSlot(backpack, EquipmentItemSlot.Back));
        }

        [Fact]
        public void TwoHandedTransitionPlansToDisplaceTheOffhand()
        {
            var character = CharacterWithInventory();
            var offhand = Weapon(EquipmentItemSlotType.OneHanded);
            Assert.True(character.Inventory.Equipment.AddOrMoveExistingItem(
                ItemTaskType.Invalid, offhand, (int)EquipmentItemSlot.Offhand));

            var incoming = Weapon(EquipmentItemSlotType.TwoHanded);
            var plan = EquipmentRuleService.Instance.Plan(
                character, incoming, EquipmentItemSlot.Mainhand);

            Assert.True(plan.IsValid);
            Assert.Single(plan.MoveToBag);
            Assert.Same(offhand, plan.MoveToBag[0]);
        }

        [Fact]
        public void OffhandTransitionPlansToDisplaceATwoHandedMainWeapon()
        {
            var character = CharacterWithInventory();
            var main = Weapon(EquipmentItemSlotType.TwoHanded);
            Assert.True(character.Inventory.Equipment.AddOrMoveExistingItem(
                ItemTaskType.Invalid, main, (int)EquipmentItemSlot.Mainhand));

            var incoming = Weapon(EquipmentItemSlotType.OneHanded);
            var plan = EquipmentRuleService.Instance.Plan(
                character, incoming, EquipmentItemSlot.Offhand);

            Assert.True(plan.IsValid);
            Assert.Single(plan.MoveToBag);
            Assert.Same(main, plan.MoveToBag[0]);
        }

        [Fact]
        public void HandTransitionFailsBeforeMutationWhenInventoryIsFull()
        {
            var character = CharacterWithInventory(1);
            Assert.True(character.Inventory.Bag.AddOrMoveExistingItem(
                ItemTaskType.Invalid, new Item { Template = new ItemTemplate { MaxCount = 1 } }));
            var offhand = Weapon(EquipmentItemSlotType.OneHanded);
            Assert.True(character.Inventory.Equipment.AddOrMoveExistingItem(
                ItemTaskType.Invalid, offhand, (int)EquipmentItemSlot.Offhand));

            var plan = EquipmentRuleService.Instance.Plan(
                character, Weapon(EquipmentItemSlotType.TwoHanded),
                EquipmentItemSlot.Mainhand);

            Assert.False(plan.IsValid);
            Assert.Equal(EquipmentValidationFailure.InventoryFull, plan.Failure);
            Assert.Same(
                offhand,
                character.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Offhand));
        }

        [Fact]
        public void NativeLevelRequirementIsValidatedBeforeMutation()
        {
            var character = CharacterWithInventory();
            character.Level = 20;
            var incoming = Weapon(EquipmentItemSlotType.OneHanded);
            incoming.Template.LevelRequirement = 30;

            var plan = EquipmentRuleService.Instance.Plan(
                character, incoming, EquipmentItemSlot.Mainhand);

            Assert.False(plan.IsValid);
            Assert.Equal(EquipmentValidationFailure.RequirementNotMet, plan.Failure);
        }

        private static Character CharacterWithInventory(byte size = 10)
        {
            var character = new CharacterMock
            {
                Level = 55,
                NumInventorySlots = size,
                NumBankSlots = size
            };
            character.Inventory = new Inventory(character);
            return character;
        }

        private static Weapon Weapon(EquipmentItemSlotType type)
        {
            return new Weapon
            {
                Template = new WeaponTemplate
                {
                    MaxCount = 1,
                    HoldableTemplate = new Holdable { SlotTypeId = (uint)type }
                }
            };
        }
    }
}
