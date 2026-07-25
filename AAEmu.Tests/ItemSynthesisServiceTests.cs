using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemSynthesisServiceTests
    {
        [Fact]
        public void PreviewUsesNativeGainExpGradeExpAndGoldFormula()
        {
            var rules = PreparedRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 3,
                EvolutionExperience = 200
            };
            var material = new Item
            {
                TemplateId = 48828,
                Grade = 0,
                Count = 4
            };

            var preview = service.CreatePreview(
                target,
                new List<SynthesisMaterialSelection>
                {
                    new() { Item = material, Count = 4 }
                },
                15);

            Assert.True(preview.IsValid, preview.FailureReason);
            Assert.Equal(400, preview.MaterialExperience);
            Assert.Equal(24800, preview.GoldCost);
            Assert.Equal(4, preview.AfterGradeId);
            Assert.Equal((uint)350, preview.AfterSectionExperience);
            Assert.Equal(15, preview.LaborCost);
        }

        [Fact]
        public void PreviewRejectsMaterialOutsideNativeRelation()
        {
            var rules = PreparedRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 3
            };
            var material = new Item
            {
                TemplateId = 99999,
                Grade = 0,
                Count = 1
            };

            var preview = service.CreatePreview(
                target,
                new List<SynthesisMaterialSelection>
                {
                    new() { Item = material, Count = 1 }
                },
                15);

            Assert.Equal(
                ItemEvolutionValidationFailure.MaterialNotAllowed,
                preview.Failure);
        }

        private static ItemEvolutionRuleService PreparedRules()
        {
            var rules = new ItemEvolutionRuleService();
            rules.RegisterItemCategory(45635, 509);
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 509,
                CategoryGroupId = 1,
                MaterialGradeLimit = 12,
                MaxEvolvingGrade = 8
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 1,
                CategoryId = 509,
                GradeId = 3,
                GainExp = 12294,
                GoldMultiplier = 62000,
                GradeExp = 250,
                BonusExpChance = 150,
                BonusExpMin = 200,
                BonusExpMax = 500,
                MaxUnitModifierNum = 3
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 2,
                CategoryId = 509,
                GradeId = 4,
                GainExp = 14791,
                GoldMultiplier = 62000,
                GradeExp = 500,
                BonusExpChance = 150,
                BonusExpMin = 200,
                BonusExpMax = 500,
                MaxUnitModifierNum = 3
            });
            rules.RegisterCategoryRelation(new ItemRndAttrCategoryRelation
            {
                Id = 1,
                CategoryGroupId = 1,
                MaterialItemId = 48828
            });
            rules.RegisterMaterial(new ItemEvolvingMaterial
            {
                ItemId = 48828,
                CategoryId = 520,
                ShowExp = true
            });
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 520,
                CategoryGroupId = 2,
                MaterialGradeLimit = 12,
                MaxEvolvingGrade = 12
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 3,
                CategoryId = 520,
                GradeId = 0,
                GainExp = 100
            });
            rules.MarkNativeCatalogueAvailable();
            return rules;
        }
    }
}
