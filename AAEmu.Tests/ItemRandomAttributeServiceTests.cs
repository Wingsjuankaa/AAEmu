using System.Linq;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemRandomAttributeServiceTests
    {
        [Fact]
        public void GradeUnlockSelectsNativeSetQuotasAndInterpolatesValues()
        {
            var rules = PreparedRules();
            var service = new ItemRandomAttributeService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 2
            };

            var result = service.ResolveForSynthesis(
                target,
                3,
                125,
                _ => 0);

            Assert.True(result.IsValid, result.FailureReason);
            Assert.Equal(new uint[] { 1001, 2001, 2003 }, result.ModifierIds);
            Assert.All(result.Values, value => Assert.True(value.Added));
            Assert.Equal(new[] { 15, 105, 305 },
                result.Values.Select(value => value.Value));
        }

        [Fact]
        public void GradeProgressRemapsExistingGroupsWithoutRerolling()
        {
            var rules = PreparedRules();
            var service = new ItemRandomAttributeService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 3
            };
            target.SetNativeRandomModifierId(0, 1001);
            target.SetNativeRandomModifierId(1, 2001);
            target.SetNativeRandomModifierId(2, 2003);

            var result = service.ResolveForSynthesis(
                target,
                4,
                0,
                _ => throw new Xunit.Sdk.XunitException(
                    "Existing native groups must not be rerolled."));

            Assert.True(result.IsValid, result.FailureReason);
            Assert.Equal(new uint[] { 1002, 2002, 2004 }, result.ModifierIds);
            Assert.All(result.Values, value => Assert.False(value.Added));
            Assert.Equal(new[] { 20, 200, 400 },
                result.Values.Select(value => value.Value));
        }

        private static ItemEvolutionRuleService PreparedRules()
        {
            var rules = new ItemEvolutionRuleService();
            rules.RegisterItemCategory(45635, 509);
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 509,
                MaxEvolvingGrade = 12
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 1,
                CategoryId = 509,
                GradeId = 3,
                GradeExp = 250,
                MaxUnitModifierNum = 3
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 2,
                CategoryId = 509,
                GradeId = 4,
                GradeExp = 500,
                MaxUnitModifierNum = 3
            });
            rules.RegisterModifierGroupSet(new ItemRndAttrUnitModifierGroupSet
            {
                Id = 125,
                CategoryId = 509,
                PickCount = 1,
                Weight = 1
            });
            rules.RegisterModifierGroupSet(new ItemRndAttrUnitModifierGroupSet
            {
                Id = 137,
                CategoryId = 509,
                PickCount = 2,
                Weight = 1
            });
            RegisterGroup(rules, 10, 125, 1, 0, 1001, 1002, 10, 20);
            RegisterGroup(rules, 20, 137, 2, 0, 2001, 2002, 100, 200);
            RegisterGroup(rules, 21, 137, 3, 1, 2003, 2004, 300, 400);
            RegisterGroup(rules, 22, 137, 4, 1, 2005, 2006, 500, 600);
            rules.MarkNativeCatalogueAvailable();
            return rules;
        }

        private static void RegisterGroup(
            ItemEvolutionRuleService rules,
            uint groupId,
            uint setId,
            uint attributeId,
            uint modifierTypeId,
            uint grade3Id,
            uint grade4Id,
            int grade3Minimum,
            int grade4Minimum)
        {
            rules.RegisterModifierGroup(new ItemRndAttrUnitModifierGroup
            {
                Id = groupId,
                GroupSetId = setId,
                UnitAttributeId = attributeId,
                UnitModifierTypeId = modifierTypeId,
                Weight = 1
            });
            rules.RegisterModifier(new ItemRndAttrUnitModifier
            {
                Id = grade3Id,
                GroupId = groupId,
                GradeId = 3,
                Minimum = grade3Minimum,
                Maximum = grade3Minimum + 10
            });
            rules.RegisterModifier(new ItemRndAttrUnitModifier
            {
                Id = grade4Id,
                GroupId = groupId,
                GradeId = 4,
                Minimum = grade4Minimum,
                Maximum = grade4Minimum + 10
            });
        }
    }
}
