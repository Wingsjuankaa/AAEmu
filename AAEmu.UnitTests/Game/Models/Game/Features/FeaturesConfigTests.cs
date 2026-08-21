using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Features;
using Microsoft.Extensions.Configuration;

namespace AAEmu.UnitTests.Game.Models.Game.Features;

/// <summary>
/// Guards the shipped <c>Configurations/Features.json</c>. The fset baseline lives in that file, so a
/// key the <see cref="Feature"/> enum does not define turns a feature off with nothing but a log line
/// to show for it.
/// </summary>
public class FeaturesConfigTests
{
    private static FeaturesConfig LoadShippedConfig()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Configurations", "Features.json");
        return new ConfigurationBuilder()
            .AddJsonFile(path, optional: false)
            .Build()
            .GetSection("Features")
            .Get<FeaturesConfig>()!;
    }

    [Test]
    public async Task ShippedConfig_Binds()
    {
        var config = LoadShippedConfig();

        await Assert.That(config).IsNotNull();
        await Assert.That(config.Flags.Count > 0).IsTrue();
    }

    [Test]
    public async Task EveryConfiguredFlag_NamesAnAddressableFeature()
    {
        var config = LoadShippedConfig();
        var fset = new FeatureSet();
        var rejected = new List<string>();

        foreach (var (name, enabled) in config.Flags)
        {
            if (!Enum.TryParse<Feature>(name, true, out var feature) || !Enum.IsDefined(feature))
                rejected.Add($"{name} (undefined)");
            else if (!fset.Set(feature, enabled))
                rejected.Add($"{name} (bit {(int)feature} is unaddressable)");
        }

        await Assert.That(string.Join(", ", rejected)).IsEqualTo(string.Empty);
    }

    [Test]
    public async Task ConfiguredFlags_ProduceTheExpectedBlob()
    {
        // Pins the shipped baseline byte-for-byte. A change here changes what the client is told this
        // server supports, so it should be a deliberate edit rather than a side effect. The scalar bytes
        // (1, 8, 10, 26) stay zero: FeaturesManager fills those from the level caps, not from Flags.
        var config = LoadShippedConfig();
        var fset = new FeatureSet();
        foreach (var (name, enabled) in config.Flags)
            fset.Set(Enum.Parse<Feature>(name, true), enabled);

        // Native doodad descriptor lookup adds byte 11 bit 2. The inventory utility row adds
        // itemSecure (byte 5 bit 5), itemRepairInBag (byte 11 bit 4),
        // itemLookConvertInBag (byte 18 bit 4) and lootGacha (byte 20 bit 0). Enchant and Pin are
        // unconditional in the r575 Lua and therefore need no fset bits.
        // Byte 17 is 0xa0, not 0x80: bit 5 is itemEvolving (141). Byte 20 also contains bit 1
        // for itemEvolvingReRoll (161), which exposes the reconstructed Replace Stat controller.
        // Byte 21 is 0x82 because bit 1 is socketExtract (169), exposing native Lunagem extraction.
        // Byte 22 is 0x91: bit 0 is blessUthstin (176), exposing Migration Scaling, and bit 4 is
        // characterInfoLivingPoint (180), exposing the native Vocation store button.
        // Item Smelting (178) remains disabled because r575 selects an incomplete recipe family.
        await Assert.That(fset.ToString()).IsEqualTo(
            "13 00 00 00 d0 29 61 00 00 0c 00 9c 2c 00 00 00 " +
            "00 a0 1b 10 03 82 91 00 04 34 00 10 01 e0 00");
    }

    [Test]
    public async Task ShippedConfig_AdvertisesNativeInventoryUtilityRowAdditively()
    {
        var flags = LoadShippedConfig().Flags;

        await Assert.That(flags[Feature.lootGacha.ToString()]).IsTrue();
        await Assert.That(flags[Feature.itemSecure.ToString()]).IsTrue();
        await Assert.That(flags[Feature.itemRepairInBag.ToString()]).IsTrue();
        await Assert.That(flags[Feature.itemLookConvertInBag.ToString()]).IsTrue();
    }

    [Test]
    public async Task ShippedConfig_AdvertisesNativeClientDoodadDescriptorLookup()
    {
        var flags = LoadShippedConfig().Flags;

        await Assert.That(flags[Feature.fset_11_2_unknown.ToString()]).IsTrue();
    }

    [Test]
    public async Task ShippedConfig_AdvertisesAttendanceAndArchePassWithoutAccountMissions()
    {
        var flags = LoadShippedConfig().Flags;

        await Assert.That(flags[Feature.account_attendance.ToString()]).IsTrue();
        await Assert.That(flags[Feature.arche_pass.ToString()]).IsTrue();
        await Assert.That(flags[Feature.archePassMissionAccount.ToString()]).IsFalse();
    }
}
