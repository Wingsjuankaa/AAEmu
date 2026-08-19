using AAEmu.Game.Models.Game;

namespace AAEmu.Game.Models.Game.Merchant;

internal readonly record struct MerchantCatalogOverrideKey(uint MerchantPackId, uint ItemId);

internal static class MerchantCatalogOverridePolicy
{
    internal static bool TryCreateKey(
        MerchantCatalogOverrideConfig entry,
        out MerchantCatalogOverrideKey key)
    {
        key = default;
        if (entry is null || entry.MerchantPackId == 0 || entry.ItemId == 0)
            return false;

        key = new MerchantCatalogOverrideKey(entry.MerchantPackId, entry.ItemId);
        return true;
    }

    internal static bool ShouldLoad(
        bool databaseEnabled,
        IReadOnlySet<MerchantCatalogOverrideKey> overrides,
        uint merchantPackId,
        uint itemId)
    {
        return databaseEnabled || overrides.Contains(new MerchantCatalogOverrideKey(merchantPackId, itemId));
    }
}
