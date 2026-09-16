using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Char.Templates;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Containers;

public class FishingEquipmentRequirementsTests
{
    [Test]
    public async Task LobbyRestoreRetainsEquippedRodBeforeActabilityIsLoaded()
    {
        var character = new CharacterMock { Level = 1 };
        var equipment = new EquipmentContainer(0, SlotType.Equipment, false, character) { Owner = character };
        var rod = new Item(123, new WeaponTemplate { Id = 35055, LevelRequirement = 10,
            ActabilityGroupId = 7, ActabilityRequirement = 120000,
            HoldableTemplate = new Holdable { SlotTypeId = (uint)EquipmentItemSlotType.TwoHanded } }, 1)
            { SlotType = SlotType.Equipment, Slot = (int)EquipmentItemSlot.Mainhand,
                _holdingContainer = equipment };
        // Inventory.Load has cleared Items, but retains each item's persisted container link.
        await Assert.That(equipment.AddOrMoveExistingItem(AAEmu.Game.Models.Game.Items.Actions.ItemTaskType.Invalid,
            rod, rod.Slot)).IsTrue();
        await Assert.That(equipment.Items).Contains(rod);
        rod._holdingContainer = null;
        await Assert.That(equipment.CanAccept(rod, rod.Slot)).IsFalse();
    }

    [Test]
    [Arguments(27309u, 10000)]
    [Arguments(27310u, 20000)]
    [Arguments(27311u, 30000)]
    [Arguments(27312u, 50000)]
    [Arguments(35055u, 120000)]
    public async Task RetailRods_RequireTheirDeclaredProficiency(uint itemId, int required)
    {
        var template = new ItemTemplate { Id = itemId, LevelRequirement = 1,
            ActabilityGroupId = 7, ActabilityRequirement = required };
        await Assert.That(EquipmentContainer.GetRequirementError(template, 55, required - 1))
            .IsEqualTo(ErrorMessageType.ActabilityNotEnoughPoint);
        await Assert.That(EquipmentContainer.GetRequirementError(template, 55, required)).IsNull();
    }

    [Test]
    public async Task UltimateRod_EquipAndUseHaveSeparateRequirements()
    {
        // Full r575 item46503 has no equip proficiency requirement. Its skill39905 owns
        // unit_req61230: kind43, group7, 150000 points, including bonuses (value3=0).
        var template = new ItemTemplate { Id = 46503, LevelRequirement = 1, ActabilityGroupId = 7 };
        await Assert.That(EquipmentContainer.GetRequirementError(template, 55, 0)).IsNull();
        var character = new CharacterMock();
        character.Actability = new CharacterActability(character);
        character.Actability.Actabilities[7] = new Actability(new ActabilityTemplate
            { Id = 7, UnitAttributeId = -1 }) { Point = 149999 };
        var requirement = new UnitReqs { Id = 61230, OwnerType = "Skill", OwnerId = 39905,
            KindType = UnitReqsKindType.ActAbilityPoint, Value1 = 7, Value2 = 150000 };
        await Assert.That(requirement.Validate(character, character).ResultKey).IsNotEqualTo(SkillResultKeys.ok);
        character.Actability.Actabilities[7].Point = 150000;
        await Assert.That(requirement.Validate(character, character).ResultKey).IsEqualTo(SkillResultKeys.ok);
    }

    [Test]
    public async Task EquipmentChecksLevelBoundsWithoutUsingCombatItemLevel()
    {
        var template = new ItemTemplate { Level = 99, LevelRequirement = 10, LevelLimit = 30 };
        await Assert.That(EquipmentContainer.GetRequirementError(template, 9, 0)).IsEqualTo(ErrorMessageType.LevelLowToEquip);
        await Assert.That(EquipmentContainer.GetRequirementError(template, 10, 0)).IsNull();
        await Assert.That(EquipmentContainer.GetRequirementError(template, 30, 0)).IsNull();
        await Assert.That(EquipmentContainer.GetRequirementError(template, 31, 0)).IsEqualTo(ErrorMessageType.LevelHighToEquip);
    }

    [Test]
    public async Task RejectBeforeMovingRod_PreservesSourceAndAllowsUnequip()
    {
        var character = new CharacterMock { Level = 55 };
        character.Actability = new CharacterActability(character);
        var equipment = new EquipmentContainer(0, SlotType.Equipment, false, character) { Owner = character };
        var rod = new Item(123, new WeaponTemplate { Id = 27309, LevelRequirement = 1,
            ActabilityGroupId = 7, ActabilityRequirement = 10000,
            HoldableTemplate = new Holdable { SlotTypeId = (uint)EquipmentItemSlotType.TwoHanded } }, 1)
            { SlotType = SlotType.Inventory, Slot = 5 };
        await Assert.That(equipment.AddOrMoveExistingItem(AAEmu.Game.Models.Game.Items.Actions.ItemTaskType.Invalid,
            rod, (int)EquipmentItemSlot.Mainhand)).IsFalse();
        await Assert.That(rod.SlotType).IsEqualTo(SlotType.Inventory);
        await Assert.That(rod.Slot).IsEqualTo(5);
        await Assert.That(equipment.Items).IsEmpty();
        await Assert.That(equipment.CanAccept(null, (int)EquipmentItemSlot.Mainhand)).IsTrue();
    }
}
