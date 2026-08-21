using AAEmu.Game.Models.Game;
using Microsoft.Extensions.Configuration;

namespace AAEmu.UnitTests.Game.Models.Game;

public class InitialConfigTests
{
    [Test]
    public async Task ShippedConfig_UsesStableMatureReferenceShardOpenTime()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Configurations", "InitialConfig.json");
        var config = new ConfigurationBuilder()
            .AddJsonFile(path, optional: false)
            .Build()
            .GetSection("InitialConfig")
            .Get<InitialConfig>()!;

        await Assert.That(config.ServerOpenTimeUnixSeconds).IsEqualTo(0x6A3D5080L);
    }
}
