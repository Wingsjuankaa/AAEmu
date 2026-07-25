using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemRandomAttributeRerollTests
    {
        [Fact]
        public void ExplicitNativeGroupReplacesOnlyTheSelectedPhysicalSlot()
        {
            var rules = BuildRules();
            var service = new ItemRandomAttributeService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 8,
                EvolutionExperience = 500
            };
            target.SetNativeRandomModifierId(0, 7001);
            target.SetNativeRandomModifierId(1, 7003);

            var result = service.ResolveReroll(
                target,
                0,
                5002,
                _ => 0);

            Assert.True(result.IsValid);
            Assert.Equal(0, result.ModifierIndex);
            Assert.Equal((uint)7001, result.BeforeModifierId);
            Assert.Equal((uint)7002, result.AfterModifierId);
            Assert.Equal((ushort)11, result.Before.UnitAttributeId);
            Assert.Equal((ushort)12, result.After.UnitAttributeId);
            Assert.Equal((uint)7003, target.GetNativeRandomModifierId(1));
        }

        [Fact]
        public void RerollRejectsAnAttributeAlreadyUsedByAnotherSlot()
        {
            var rules = BuildRules();
            var service = new ItemRandomAttributeService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 8
            };
            target.SetNativeRandomModifierId(0, 7001);
            target.SetNativeRandomModifierId(1, 7003);

            var result = service.ResolveReroll(
                target,
                0,
                5003,
                _ => 0);

            Assert.False(result.IsValid);
            Assert.Equal(
                ItemEvolutionValidationFailure.RerollGroupInvalid,
                result.Failure);
        }

        private static ItemEvolutionRuleService BuildRules()
        {
            var rules = new ItemEvolutionRuleService();
            rules.RegisterItemCategory(45635, 10);
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 10,
                MaxEvolvingGrade = 12
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 100,
                CategoryId = 10,
                GradeId = 8,
                GradeExp = 1000,
                MaxUnitModifierNum = 3
            });
            rules.RegisterModifierGroupSet(
                new ItemRndAttrUnitModifierGroupSet
                {
                    Id = 4000,
                    CategoryId = 10,
                    PickCount = 3
                });
            RegisterModifier(rules, 5001, 7001, 11);
            RegisterModifier(rules, 5002, 7002, 12);
            RegisterModifier(rules, 5003, 7003, 13);
            return rules;
        }

        private static void RegisterModifier(
            ItemEvolutionRuleService rules,
            uint groupId,
            uint modifierId,
            uint attributeId)
        {
            rules.RegisterModifierGroup(new ItemRndAttrUnitModifierGroup
            {
                Id = groupId,
                GroupSetId = 4000,
                UnitAttributeId = attributeId,
                UnitModifierTypeId = 1,
                Weight = 1
            });
            rules.RegisterModifier(new ItemRndAttrUnitModifier
            {
                Id = modifierId,
                GroupId = groupId,
                GradeId = 8,
                Minimum = 100,
                Maximum = 200
            });
        }
    }
}
