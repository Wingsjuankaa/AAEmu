using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemRegradeRuleServiceTests
    {
        [Fact]
        public void ProfileResolvesOnlyExplicitNativeItemMapping()
        {
            var profile = PreparedService().GetProfile(45000, 7);

            Assert.True(profile.HasNativeRatio);
            Assert.Equal(7500, profile.Ratio.Success);
            Assert.Equal(1000, profile.Ratio.Cost);
        }

        [Fact]
        public void UnknownItemDoesNotFallBackToHistoricalGroup()
        {
            var profile = PreparedService().GetProfile(45001, 7);

            Assert.False(profile.HasNativeRatio);
            Assert.Equal(0, profile.GroupId);
        }

        [Fact]
        public void SupportRetainsAllAa8Fields()
        {
            var service = PreparedService();
            service.RegisterSupport(new ItemGradeEnchantingSupportDefinition
            {
                ItemId = 50000,
                AddDisableRatio = 250,
                Icons = 1358954502,
                ImplementationFlags = 31,
                RequiredScaleMinId = 2,
                RequiredScaleMaxId = 8
            });

            var support = service.GetSupport(50000);

            Assert.Equal(250, support.AddDisableRatio);
            Assert.Equal(1358954502, support.Icons);
            Assert.Equal(31, support.ImplementationFlags);
            Assert.Equal(2, support.RequiredScaleMinId);
            Assert.Equal(8, support.RequiredScaleMaxId);
        }

        [Fact]
        public void ClearRemovesCatalogueAndAvailability()
        {
            var service = PreparedService();
            service.MarkNativeCatalogueAvailable();

            service.Clear();

            Assert.False(service.NativeCatalogueAvailable);
            Assert.False(service.GetProfile(45000, 7).HasNativeRatio);
        }

        [Fact]
        public void MutationRemainsFailClosed()
        {
            Assert.False(PreparedService().NativeMutationEnabled);
        }

        private static ItemRegradeRuleService PreparedService()
        {
            var service = new ItemRegradeRuleService();
            service.RegisterGroup(new ItemEnchantRatioGroup
            {
                Id = 4,
                ItemImplId = 28,
                KindId = 2
            });
            service.RegisterRatio(new ItemEnchantRatio
            {
                GroupId = 4,
                Grade = 7,
                Success = 7500,
                Cost = 1000
            });
            service.RegisterItem(45000, 4);
            return service;
        }
    }
}
