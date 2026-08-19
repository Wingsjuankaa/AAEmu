using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Merchant;
using Microsoft.Extensions.Configuration;

namespace AAEmu.UnitTests.Game.Models.Game.Merchant;

public class MerchantCatalogOverridePolicyTests
{
    private static MerchantCatalogConfig LoadShippedConfig()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Configurations", "MerchantCatalog.json");
        return new ConfigurationBuilder()
            .AddJsonFile(path, optional: false)
            .Build()
            .GetSection("MerchantCatalog")
            .Get<MerchantCatalogConfig>()!;
    }

    [Test]
    public async Task ShippedConfig_ContainsOnlyTheNineAuditedRelationships()
    {
        var entries = LoadShippedConfig().EnableDisabledGoods;
        var keys = entries
            .Select(entry => new MerchantCatalogOverrideKey(entry.MerchantPackId, entry.ItemId))
            .ToHashSet();
        var expected = new HashSet<MerchantCatalogOverrideKey>
        {
            new(119, 47868),
            new(119, 47869),
            new(119, 51185),
            new(119, 53424),
            new(120, 47868),
            new(120, 47869),
            new(120, 51185),
            new(120, 53424),
            new(145, 54335)
        };

        await Assert.That(entries.Count).IsEqualTo(expected.Count);
        await Assert.That(keys.SetEquals(expected)).IsTrue();
        await Assert.That(entries.All(entry => !string.IsNullOrWhiteSpace(entry.Reason))).IsTrue();
    }

    [Test]
    public async Task DisabledGood_RequiresExactPackAndItemPair()
    {
        var overrides = new HashSet<MerchantCatalogOverrideKey>
        {
            new(119, 47868)
        };

        await Assert.That(MerchantCatalogOverridePolicy.ShouldLoad(false, overrides, 119, 47868)).IsTrue();
        await Assert.That(MerchantCatalogOverridePolicy.ShouldLoad(false, overrides, 120, 47868)).IsFalse();
        await Assert.That(MerchantCatalogOverridePolicy.ShouldLoad(false, overrides, 119, 47869)).IsFalse();
    }

    [Test]
    public async Task RetailEnabledGood_LoadsWithoutOverride()
    {
        var overrides = new HashSet<MerchantCatalogOverrideKey>();

        await Assert.That(MerchantCatalogOverridePolicy.ShouldLoad(true, overrides, 145, 47866)).IsTrue();
    }

    [Test]
    [Arguments(0u, 54335u)]
    [Arguments(145u, 0u)]
    public async Task ZeroIdentifier_IsRejected(uint packId, uint itemId)
    {
        var entry = new MerchantCatalogOverrideConfig
        {
            MerchantPackId = packId,
            ItemId = itemId
        };

        await Assert.That(MerchantCatalogOverridePolicy.TryCreateKey(entry, out _)).IsFalse();
    }

    [Test]
    public async Task ValidConfiguration_ProducesStableKey()
    {
        var entry = new MerchantCatalogOverrideConfig
        {
            MerchantPackId = 145,
            ItemId = 54335
        };

        var valid = MerchantCatalogOverridePolicy.TryCreateKey(entry, out var key);

        await Assert.That(valid).IsTrue();
        await Assert.That(key).IsEqualTo(new MerchantCatalogOverrideKey(145, 54335));
    }
}
