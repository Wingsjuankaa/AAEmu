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

        [Fact]
        public void TransactionPlanUsesNativePermilleBonusAndCrossesGrades()
        {
            var rules = PreparedRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 3,
                EvolutionExperience = 200
            };
            var preview = service.CreatePreview(
                target,
                new List<SynthesisMaterialSelection>
                {
                    new()
                    {
                        Item = new Item
                        {
                            TemplateId = 48828,
                            Grade = 0,
                            Count = 4
                        },
                        Count = 4
                    }
                },
                15);

            var plan = service.CreateTransactionPlan(
                preview,
                149,
                500,
                false);

            Assert.Equal(200, plan.BonusExperience);
            Assert.Equal(600, plan.ResolvedExperience);
            Assert.Equal(5, plan.AfterGradeId);
            Assert.Equal((uint)50, plan.AfterSectionExperience);
        }

        [Fact]
        public void TransactionPlanDoesNotApplyBonusAtChanceBoundary()
        {
            var rules = PreparedRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 45635,
                Grade = 3,
                EvolutionExperience = 200
            };
            var preview = service.CreatePreview(
                target,
                new List<SynthesisMaterialSelection>
                {
                    new()
                    {
                        Item = new Item
                        {
                            TemplateId = 48828,
                            Grade = 0,
                            Count = 4
                        },
                        Count = 4
                    }
                },
                15);

            var plan = service.CreateTransactionPlan(
                preview,
                150,
                500,
                false);

            Assert.Equal(0, plan.BonusExperience);
            Assert.Equal(400, plan.ResolvedExperience);
            Assert.Equal(4, plan.AfterGradeId);
            Assert.Equal((uint)350, plan.AfterSectionExperience);
        }

        [Fact]
        public void GradeProgressionUsesNativeOrderInsteadOfNumericId()
        {
            var rules = PreparedExplorerRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 48023,
                Grade = 0,
                EvolutionExperience = 0
            };

            var resolved = service.TryResolveGrades(
                target,
                11,
                out var gradeId,
                out var sectionExperience);

            Assert.True(resolved);
            Assert.Equal(2, gradeId);
            Assert.Equal((uint)0, sectionExperience);
        }

        [Fact]
        public void ExplorerInfusionTraversesCrudeZeroCostStageInNativeOrder()
        {
            var rules = PreparedExplorerRules();
            var service = new ItemSynthesisService(rules);
            var target = new EquipItem
            {
                TemplateId = 48023,
                Grade = 1,
                EvolutionExperience = 0
            };

            var resolved = service.TryResolveGrades(
                target,
                49,
                out var gradeId,
                out var sectionExperience);

            Assert.True(resolved);
            Assert.Equal(4, gradeId);
            Assert.Equal((uint)0, sectionExperience);
        }

        [Fact]
        public void ExplorerRankOneInfusionPreviewEndsAtArcaneWithOneOverflowExp()
        {
            var rules = PreparedExplorerRules();
            var service = new ItemSynthesisService(rules);
            var preview = service.CreatePreview(
                new EquipItem
                {
                    TemplateId = 48023,
                    Grade = 0,
                    EvolutionExperience = 0
                },
                new List<SynthesisMaterialSelection>
                {
                    new()
                    {
                        Item = new Item
                        {
                            TemplateId = 48845,
                            Grade = 2,
                            Count = 1
                        },
                        Count = 1
                    }
                },
                15);

            Assert.True(preview.IsValid, preview.FailureReason);
            Assert.Equal(50, preview.MaterialExperience);
            Assert.Equal(4, preview.AfterGradeId);
            Assert.Equal((uint)1, preview.AfterSectionExperience);
        }

        private static ItemEvolutionRuleService PreparedRules()
        {
            var rules = new ItemEvolutionRuleService();
            RegisterStandardGradeOrder(rules);
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
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 4,
                CategoryId = 509,
                GradeId = 5,
                GainExp = 17000,
                GoldMultiplier = 62000,
                GradeExp = 1000,
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

        private static ItemEvolutionRuleService PreparedExplorerRules()
        {
            var rules = new ItemEvolutionRuleService();
            RegisterStandardGradeOrder(rules);
            rules.RegisterItemCategory(48023, 635);
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 635,
                CategoryGroupId = 11,
                MaterialGradeLimit = 255,
                MaxEvolvingGrade = 4
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 1,
                CategoryId = 635,
                GradeId = 1,
                GradeExp = 0,
                GoldMultiplier = 24702
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 2,
                CategoryId = 635,
                GradeId = 0,
                GradeExp = 11,
                GoldMultiplier = 24702
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 3,
                CategoryId = 635,
                GradeId = 2,
                GradeExp = 16,
                GoldMultiplier = 24702
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 4,
                CategoryId = 635,
                GradeId = 3,
                GradeExp = 22,
                GoldMultiplier = 24702
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 5,
                CategoryId = 635,
                GradeId = 4,
                GradeExp = 0,
                GoldMultiplier = 24702
            });
            rules.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 672,
                CategoryGroupId = 12,
                MaterialGradeLimit = 255,
                MaxEvolvingGrade = 12
            });
            rules.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 6,
                CategoryId = 672,
                GradeId = 2,
                GainExp = 50,
                GoldMultiplier = 1000,
                GradeExp = 0
            });
            rules.RegisterMaterial(new ItemEvolvingMaterial
            {
                ItemId = 48845,
                CategoryId = 672,
                ShowExp = true
            });
            rules.MarkNativeCatalogueAvailable();
            return rules;
        }

        private static void RegisterStandardGradeOrder(
            ItemEvolutionRuleService rules)
        {
            // AA8 orders Crude (id 1) before Basic (id 0).
            rules.RegisterGrade(1, 0);
            rules.RegisterGrade(0, 1);
            for (var gradeId = 2; gradeId <= 12; gradeId++)
                rules.RegisterGrade(gradeId, gradeId);
        }
    }
}
