using AAEmu.Game.Models.Game.Features;

namespace AAEmu.Game.Models.Game.Merchant;

/// <summary>
/// Closes the actorless purchase contract used by the Honor and Vocation buttons in Character Info.
/// The AA10 client sends zero actor ids and zero shop type, so only the server-owned open type and
/// its retail <c>content_configs</c> mapping may select stock.
/// </summary>
internal static class CharacterPanelStorePolicy
{
    internal const byte VocationOpenType = 1;
    internal const byte HonorOpenType = 2;

    internal const int MerchantPackContentConfigKind = 29;
    internal const uint VocationContentConfigId = 100;
    internal const uint HonorContentConfigId = 101;

    internal static bool TryGetOpenType(uint contentConfigId, int kindId, out byte openType)
    {
        openType = contentConfigId switch
        {
            VocationContentConfigId when kindId == MerchantPackContentConfigKind => VocationOpenType,
            HonorContentConfigId when kindId == MerchantPackContentConfigKind => HonorOpenType,
            _ => 0
        };
        return openType != 0;
    }

    internal static bool CanResolve(
        FeatureSet features,
        uint npcObjId,
        uint doodadObjId,
        uint shopType,
        bool useAaPoint,
        int buyCount,
        int buybackCount,
        byte openType)
    {
        if (features == null ||
            npcObjId != 0 ||
            doodadObjId != 0 ||
            shopType != 0 ||
            useAaPoint ||
            buyCount <= 0 ||
            buybackCount != 0 ||
            !features.Check(Feature.shopOnUI) ||
            features.Check(Feature.blockSpendableGamePoint))
            return false;

        return openType switch
        {
            VocationOpenType => features.Check(Feature.characterInfoLivingPoint),
            HonorOpenType => true,
            _ => false
        };
    }
}
