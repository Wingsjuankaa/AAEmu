using System.Linq;

using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class ItemCapabilityCoverageServiceTests
    {
        [Fact]
        public void RegistersIndependentDimensionsWithoutChangingDefinitionCoverage()
        {
            var service = new ItemCapabilityCoverageService();
            service.Register(
                new ItemCapabilityCoverage
                {
                    ItemId = 45731,
                    Dimension = "descriptor",
                    State = ItemCapabilityCoverageState.Confirmed
                });
            service.Register(
                new ItemCapabilityCoverage
                {
                    ItemId = 45731,
                    Dimension = "protocol",
                    State = ItemCapabilityCoverageState.Unknown,
                    BlockerCode = "protocol_unknown"
                });

            var coverage = service.Get(45731);

            Assert.Equal(2, coverage.Count);
            Assert.Equal(
                ItemCapabilityCoverageState.Confirmed,
                coverage.Single(value => value.Dimension == "descriptor").State);
            Assert.Equal(
                "protocol_unknown",
                coverage.Single(value => value.Dimension == "protocol").BlockerCode);
            Assert.Empty(service.Get(1));
        }
    }
}
