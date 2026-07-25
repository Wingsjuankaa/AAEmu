using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemEvolutionRuleServiceTests
    {
        [Fact]
        public void ProfileResolvesNativeCategoryAndGradeProperty()
        {
            var service = PreparedService();

            var profile = service.GetProfile(45000, 7);

            Assert.True(profile.HasSynthesisDefinition);
            Assert.Equal((uint)10, profile.CategoryId);
            Assert.NotNull(profile.Property);
            Assert.Equal(1200, profile.Property.GradeExp);
            Assert.Single(profile.Elements);
        }

        [Fact]
        public void MaterialCanResolveCategoryWithoutEquipmentDefinition()
        {
            var service = PreparedService();
            service.RegisterMaterial(new ItemEvolvingMaterial
            {
                ItemId = 49000,
                CategoryId = 10,
                ShowExp = true
            });

            var profile = service.GetProfile(49000, 7);

            Assert.True(profile.IsSynthesisMaterial);
            Assert.True(profile.HasSynthesisDefinition);
        }

        [Fact]
        public void AwakeningMappingsAreFilteredByNativeSourceGrade()
        {
            var service = PreparedService();
            service.RegisterMappingGroup(new ItemChangeMappingGroup
            {
                Id = 3,
                Success = 7500,
                Selectable = true
            });
            service.RegisterMapping(new ItemChangeMapping
            {
                Id = 1,
                MappingGroupId = 3,
                SourceItemId = 45000,
                SourceGradeId = 7,
                TargetItemId = 45001,
                TargetGradeId = 8
            });
            service.RegisterMapping(new ItemChangeMapping
            {
                Id = 2,
                MappingGroupId = 3,
                SourceItemId = 45000,
                SourceGradeId = 8,
                TargetItemId = 45002,
                TargetGradeId = 9
            });

            var profile = service.GetProfile(45000, 7);

            Assert.Single(profile.AwakeningMappings);
            Assert.Equal((uint)45001, profile.AwakeningMappings[0].TargetItemId);
            Assert.Equal(7500, service.GetMappingGroup(3).Success);
        }

        [Fact]
        public void ClearRemovesCatalogueAndAvailability()
        {
            var service = PreparedService();
            service.MarkNativeCatalogueAvailable();

            service.Clear();

            Assert.False(service.NativeCatalogueAvailable);
            Assert.False(service.GetProfile(45000, 7).HasSynthesisDefinition);
        }

        [Fact]
        public void ProfileExposesNativeMaterialRelationsAndModifierClosure()
        {
            var service = PreparedService();
            service.RegisterCategoryRelation(new ItemRndAttrCategoryRelation
            {
                Id = 1,
                CategoryGroupId = 1,
                MaterialItemId = 49000
            });
            service.RegisterModifierGroupSet(new ItemRndAttrUnitModifierGroupSet
            {
                Id = 40,
                CategoryId = 10,
                PickCount = 1
            });
            service.RegisterModifierGroup(new ItemRndAttrUnitModifierGroup
            {
                Id = 50,
                GroupSetId = 40,
                UnitAttributeId = 1,
                Weight = 1
            });
            service.RegisterModifier(new ItemRndAttrUnitModifier
            {
                Id = 60,
                GroupId = 50,
                GradeId = 7,
                Minimum = 10,
                Maximum = 12
            });

            var profile = service.GetProfile(45000, 7);

            Assert.Contains((uint)49000, profile.ValidMaterialItemIds);
            Assert.Single(profile.ModifierGroupSets);
            Assert.Single(service.GetModifierGroups(40));
            Assert.Equal((uint)60, service.GetModifier(50, 7).Id);
        }

        [Fact]
        public void EvolutionStateUsesConfirmedAa8DetailPositions()
        {
            var item = new EquipItem
            {
                TemplateId = 45635,
                Grade = 8,
                EvolutionExperience = 12345,
                EvolveChance = 4000,
                MappingFailBonus = 2
            };
            item.SetNativeRandomModifierId(0, 7001);
            item.SetNativeRandomModifierId(4, 7005);

            var state = ItemEvolutionStateService.Instance.Read(item);

            Assert.Equal((uint)12345, state.SectionExperience);
            Assert.Equal((uint)7001, state.RandomModifierIds[0]);
            Assert.Equal((uint)7005, state.RandomModifierIds[4]);
            Assert.Equal((uint)0, item.GemIds[EquipItem.NativeSocketStartIndex]);
        }

        [Fact]
        public void AwakeningReactiveIsIndexedByItemAndMappingGroup()
        {
            var service = new ItemEvolutionRuleService();
            service.RegisterAwakeningReactive(new ItemAwakeningReactive
            {
                ItemId = 45908,
                SkillId = 39332,
                MappingGroupId = 9,
                ConsumeCount = 25,
                LaborCost = 300,
                NativeValue2 = 20,
                NativeValue4 = 2
            });

            var byItem = service.GetAwakeningReactive(45908);
            Assert.NotNull(byItem);
            Assert.Equal((uint)9, byItem.MappingGroupId);
            Assert.Equal(25, byItem.ConsumeCount);
            Assert.Single(service.GetAwakeningReactives(9));
        }

        private static ItemEvolutionRuleService PreparedService()
        {
            var service = new ItemEvolutionRuleService();
            service.RegisterItemCategory(45000, 10);
            service.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 10,
                CurrencyId = 500,
                CategoryGroupId = 1,
                MaxEvolvingGrade = 12
            });
            service.RegisterProperty(new ItemRndAttrCategoryProperty
            {
                Id = 1,
                CategoryId = 10,
                GradeId = 7,
                GradeExp = 1200
            });
            service.RegisterElement(new ItemRndAttrCategoryElement
            {
                Id = 1,
                CategoryId = 10,
                Level = 1,
                RequiredExp = 100
            });
            return service;
        }
    }
}
