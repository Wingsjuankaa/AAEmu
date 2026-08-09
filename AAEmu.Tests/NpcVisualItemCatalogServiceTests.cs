using System;

using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class NpcVisualItemCatalogServiceTests
    {
        [Fact]
        public void AllowsOnlyExplicitNativePresentationIds()
        {
            var service = new NpcVisualItemCatalogService();

            service.Register(16066);
            service.Register(25269);
            service.Register(16066);

            Assert.True(service.CatalogueAvailable);
            Assert.Equal(2, service.Count);
            Assert.True(service.CanCreatePresentationItem(16066));
            Assert.True(service.CanCreatePresentationItem(25269));
            Assert.False(service.CanCreatePresentationItem(45731));

            service.Clear();

            Assert.False(service.CatalogueAvailable);
            Assert.Equal(0, service.Count);
            Assert.False(service.CanCreatePresentationItem(16066));
        }

        [Fact]
        public void RejectsZeroAsAnInvalidPresentationItemId()
        {
            var service = new NpcVisualItemCatalogService();

            Assert.Throws<ArgumentOutOfRangeException>(() => service.Register(0));
        }
    }
}
