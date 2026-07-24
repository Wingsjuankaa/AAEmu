using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class ItemSocketRuleServiceTests
    {
        [Fact]
        public void NativeLunagemIsBlockedWhenClientProbabilityIsUnavailable()
        {
            var service = PreparedService();
            service.RegisterDefinition(new ItemSocketDefinition
            {
                ItemId = 29882,
                Kind = ItemSocketDefinitionKind.Lunagem,
                EquipSlotGroupId = 12,
                ItemSocketChanceId = 4
            });
            service.RegisterChance(new ItemSocketChanceDefinition { Id = 4, CostRatio = 3 });

            var result = service.Validate(Target(), Reagent(29882));

            Assert.False(result.IsValid);
            Assert.Equal(ItemSocketValidationFailure.ProbabilityUnavailable, result.Failure);
            Assert.Contains("socket0", result.Reason);
        }

        [Fact]
        public void NativeLunagemUsesRecoveredChanceForCurrentSocketIndex()
        {
            var service = PreparedService();
            service.RegisterDefinition(new ItemSocketDefinition
            {
                ItemId = 29882,
                Kind = ItemSocketDefinitionKind.Lunagem,
                EquipSlotGroupId = 12,
                ItemSocketChanceId = 4
            });
            var chance = new ItemSocketChanceDefinition { Id = 4, CostRatio = 3 };
            chance.SocketChances[0] = 8750;
            service.RegisterChance(chance);

            var result = service.Validate(Target(), Reagent(29882));

            Assert.True(result.IsValid);
            Assert.Equal(8750, result.SuccessChance);
            Assert.Equal(5, result.MaximumSockets);
        }

        [Fact]
        public void SlotGroupIsValidatedBeforeAnyMutation()
        {
            var service = PreparedService();
            service.RegisterDefinition(new ItemSocketDefinition
            {
                ItemId = 29882,
                Kind = ItemSocketDefinitionKind.Lunagem,
                EquipSlotGroupId = 13,
                ItemSocketChanceId = 4
            });
            service.RegisterSlotGroupMember(13, (uint)EquipmentItemSlotType.TwoHanded);

            var result = service.Validate(Target(), Reagent(29882));

            Assert.False(result.IsValid);
            Assert.Equal(ItemSocketValidationFailure.SlotMismatch, result.Failure);
        }

        [Fact]
        public void SocketLimitUsesPhysicalSlotAndTargetGrade()
        {
            var service = PreparedService(maximumSockets: 1);
            service.RegisterDefinition(new ItemSocketDefinition
            {
                ItemId = 29882,
                Kind = ItemSocketDefinitionKind.Lunagem,
                EquipSlotGroupId = 12,
                ItemSocketChanceId = 4
            });
            var target = Target();
            target.GemIds[0] = 30000;

            var result = service.Validate(target, Reagent(29882));

            Assert.False(result.IsValid);
            Assert.Equal(ItemSocketValidationFailure.SocketsFull, result.Failure);
        }

        private static ItemSocketRuleService PreparedService(int maximumSockets = 5)
        {
            var service = new ItemSocketRuleService();
            service.MarkNativeCatalogueAvailable();
            service.RegisterSlotGroupMember(12, (uint)EquipmentItemSlotType.OneHanded);
            service.RegisterSocketLimit(
                (uint)EquipmentItemSlotType.OneHanded,
                3,
                maximumSockets);
            return service;
        }

        private static Weapon Target()
        {
            return new Weapon
            {
                Grade = 3,
                TemplateId = 1000,
                Template = new WeaponTemplate
                {
                    Id = 1000,
                    Level = 55,
                    HoldableTemplate = new Holdable
                    {
                        SlotTypeId = (uint)EquipmentItemSlotType.OneHanded
                    }
                }
            };
        }

        private static Item Reagent(uint templateId)
        {
            return new Item
            {
                TemplateId = templateId,
                Template = new ItemTemplate { Id = templateId }
            };
        }
    }
}
