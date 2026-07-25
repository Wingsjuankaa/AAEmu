using System;
using System.Collections.Generic;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class ItemAwakeningServiceTests
    {
        [Fact]
        public void NaturalFailureAddsNativeFivePercentFailstack()
        {
            var service = CreateService();
            var preview = CreatePreview();

            var plan = service.CreateTransactionPlan(
                preview,
                1000,
                9999,
                EvolutionTestMode.Natural,
                _ => 0);

            Assert.False(plan.Success);
            Assert.False(plan.Crystallized);
            Assert.Equal(ItemChangeMappingResult.Fail, plan.Result);
            Assert.Equal(5, plan.AfterFailBonus);
        }

        [Fact]
        public void NaturalCrystallizationUsesNativeBasisPointRatio()
        {
            var service = CreateService();
            var preview = CreatePreview();

            var plan = service.CreateTransactionPlan(
                preview,
                1000,
                2499,
                EvolutionTestMode.Natural,
                _ => 0);

            Assert.False(plan.Success);
            Assert.True(plan.Crystallized);
            Assert.Equal(
                ItemChangeMappingResult.FailDisableEnchant,
                plan.Result);
        }

        [Fact]
        public void ForcedSuccessPreservesRequirementsButControlsResolution()
        {
            var service = CreateService(
                new uint[] { 7001, 7002, 7003 });
            var preview = CreatePreview();

            var plan = service.CreateTransactionPlan(
                preview,
                9999,
                9999,
                EvolutionTestMode.Success,
                _ => 0);

            Assert.True(plan.Success);
            Assert.Equal(ItemChangeMappingResult.Success, plan.Result);
            Assert.Equal(0, plan.AfterFailBonus);
            Assert.Equal(
                new uint[] { 7001, 7002, 7003 },
                plan.AfterModifierIds);
        }

        [Fact]
        public void ExplicitFailModeNeverCrystallizes()
        {
            var service = CreateService();
            var preview = CreatePreview();

            var plan = service.CreateTransactionPlan(
                preview,
                0,
                0,
                EvolutionTestMode.Fail,
                _ => 0);

            Assert.False(plan.Success);
            Assert.False(plan.Crystallized);
            Assert.Equal(ItemChangeMappingResult.Fail, plan.Result);
        }

        private static ItemAwakeningService CreateService(
            IReadOnlyList<uint> inheritedModifierIds = null)
        {
            return new ItemAwakeningService(
                new ItemEvolutionRuleService(),
                new StubAttributeService(
                    inheritedModifierIds ?? Array.Empty<uint>()));
        }

        private static AwakeningPreview CreatePreview()
        {
            var template = new EquipItemTemplate
            {
                Id = 45635,
                BindType = ItemBindType.Normal
            };
            var target = new EquipItem(77, template, 1)
            {
                Grade = 8,
                MappingFailBonus = 0
            };
            return new AwakeningPreview
            {
                Target = target,
                Mapping = new ItemChangeMapping
                {
                    Id = 112,
                    MappingGroupId = 9,
                    SourceGradeId = 8,
                    SourceItemId = 45635,
                    TargetGradeId = -1,
                    TargetItemId = 45828
                },
                MappingGroup = new ItemChangeMappingGroup
                {
                    Id = 9,
                    Success = 1000,
                    Disable = 2500,
                    FailBonus = 500,
                    EvolvingExpInherit = true
                },
                Reactive = new ItemAwakeningReactive
                {
                    ItemId = 45908,
                    SkillId = 39332,
                    MappingGroupId = 9,
                    ConsumeCount = 25,
                    LaborCost = 300
                },
                TargetGradeId = 8,
                BaseSuccessBasisPoints = 1000,
                EffectiveSuccessBasisPoints = 1000,
                CrystallizationBasisPoints = 2500
            };
        }

        private sealed class StubAttributeService
            : IItemRandomAttributeService
        {
            private readonly IReadOnlyList<uint> _modifierIds;

            public StubAttributeService(IReadOnlyList<uint> modifierIds)
            {
                _modifierIds = modifierIds;
            }

            public IReadOnlyList<ItemRndAttrUnitModifierGroupSet>
                GetAvailableGroupSets(EquipItem target) =>
                Array.Empty<ItemRndAttrUnitModifierGroupSet>();

            public ItemRandomAttributeResolution ResolveForSynthesis(
                EquipItem target,
                int afterGradeId,
                uint afterSectionExperience,
                Func<int, int> nextRandom) =>
                throw new NotSupportedException();

            public ItemRandomAttributeResolution ResolveForAwakening(
                EquipItem source,
                uint targetTemplateId,
                int targetGradeId,
                Func<int, int> nextRandom) =>
                new()
                {
                    IsValid = true,
                    ModifierIds = _modifierIds
                };

            public IReadOnlyList<ItemRandomAttributeValue> GetCurrentValues(
                EquipItem target) =>
                Array.Empty<ItemRandomAttributeValue>();
        }
    }
}
