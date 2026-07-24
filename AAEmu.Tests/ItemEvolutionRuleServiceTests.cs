using AAEmu.Game.Models.Game.Items.Services;

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

        private static ItemEvolutionRuleService PreparedService()
        {
            var service = new ItemEvolutionRuleService();
            service.RegisterItemCategory(45000, 10);
            service.RegisterCategory(new ItemRndAttrCategory
            {
                Id = 10,
                CurrencyId = 500,
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
