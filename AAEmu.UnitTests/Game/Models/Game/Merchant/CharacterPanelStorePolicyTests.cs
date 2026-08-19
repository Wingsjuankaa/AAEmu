using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Merchant;

namespace AAEmu.UnitTests.Game.Models.Game.Merchant;

public class CharacterPanelStorePolicyTests
{
    private static FeatureSet EnabledFeatures()
    {
        var features = new FeatureSet();
        features.Set(Feature.shopOnUI, true);
        features.Set(Feature.characterInfoLivingPoint, true);
        return features;
    }

    [Test]
    [Arguments(CharacterPanelStorePolicy.VocationContentConfigId, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(CharacterPanelStorePolicy.HonorContentConfigId, CharacterPanelStorePolicy.HonorOpenType)]
    public async Task RetailContentConfig_MapsToNativeOpenType(uint configId, byte expectedOpenType)
    {
        var mapped = CharacterPanelStorePolicy.TryGetOpenType(
            configId,
            CharacterPanelStorePolicy.MerchantPackContentConfigKind,
            out var openType);

        await Assert.That(mapped).IsTrue();
        await Assert.That(openType).IsEqualTo(expectedOpenType);
    }

    [Test]
    [Arguments(CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(CharacterPanelStorePolicy.HonorOpenType)]
    public async Task NativeActorlessWire_IsAcceptedForSupportedStore(byte openType)
    {
        var accepted = CharacterPanelStorePolicy.CanResolve(
            EnabledFeatures(),
            npcObjId: 0,
            doodadObjId: 0,
            shopType: 0,
            useAaPoint: false,
            buyCount: 1,
            buybackCount: 0,
            openType);

        await Assert.That(accepted).IsTrue();
    }

    [Test]
    [Arguments(1u, 0u, 0u, false, 1, 0, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 1u, 0u, false, 1, 0, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 0u, 3u, false, 1, 0, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 0u, 0u, true, 1, 0, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 0u, 0u, false, 0, 0, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 0u, 0u, false, 1, 1, CharacterPanelStorePolicy.VocationOpenType)]
    [Arguments(0u, 0u, 0u, false, 1, 0, 3)]
    public async Task NonNativeOrUnsupportedContext_IsRejected(
        uint npcObjId,
        uint doodadObjId,
        uint shopType,
        bool useAaPoint,
        int buyCount,
        int buybackCount,
        byte openType)
    {
        var accepted = CharacterPanelStorePolicy.CanResolve(
            EnabledFeatures(),
            npcObjId,
            doodadObjId,
            shopType,
            useAaPoint,
            buyCount,
            buybackCount,
            openType);

        await Assert.That(accepted).IsFalse();
    }

    [Test]
    public async Task VocationRequiresItsVisibilityFeature()
    {
        var features = EnabledFeatures();
        features.Set(Feature.characterInfoLivingPoint, false);

        var accepted = CharacterPanelStorePolicy.CanResolve(
            features, 0, 0, 0, false, 1, 0, CharacterPanelStorePolicy.VocationOpenType);

        await Assert.That(accepted).IsFalse();
    }

    [Test]
    public async Task SpendablePointBlock_DisablesBothDirectStores()
    {
        var features = EnabledFeatures();
        features.Set(Feature.blockSpendableGamePoint, true);

        var vocation = CharacterPanelStorePolicy.CanResolve(
            features, 0, 0, 0, false, 1, 0, CharacterPanelStorePolicy.VocationOpenType);
        var honor = CharacterPanelStorePolicy.CanResolve(
            features, 0, 0, 0, false, 1, 0, CharacterPanelStorePolicy.HonorOpenType);

        await Assert.That(vocation).IsFalse();
        await Assert.That(honor).IsFalse();
    }
}
