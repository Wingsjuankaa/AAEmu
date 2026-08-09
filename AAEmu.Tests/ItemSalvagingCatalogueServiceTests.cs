using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemSalvagingCatalogueServiceTests
    {
        [Fact]
        public void CoverageKeepsNativeRolesSeparate()
        {
            var service = new ItemSalvagingCatalogueService();
            service.RegisterReagent(45000);
            service.RegisterReagent(45000);
            service.RegisterProduct(45000);
            service.RegisterSmeltingItem(45000);

            var coverage = service.GetCoverage(45000);

            Assert.Equal(2, coverage.ReagentDefinitions);
            Assert.Equal(1, coverage.ProductDefinitions);
            Assert.Equal(1, coverage.SmeltingDefinitions);
            Assert.True(coverage.HasConversionDefinition);
            Assert.True(coverage.HasSmeltingDefinition);
        }

        [Fact]
        public void UnknownItemHasNoFallbackCoverage()
        {
            var service = new ItemSalvagingCatalogueService();

            var coverage = service.GetCoverage(45001);

            Assert.False(coverage.HasConversionDefinition);
            Assert.False(coverage.HasSmeltingDefinition);
        }

        [Fact]
        public void ClearRemovesCoverageAndAvailability()
        {
            var service = new ItemSalvagingCatalogueService();
            service.RegisterReagent(45000);
            service.MarkNativeCatalogueAvailable();

            service.Clear();

            Assert.False(service.NativeCatalogueAvailable);
            Assert.False(service.GetCoverage(45000).HasConversionDefinition);
        }
    }
}
