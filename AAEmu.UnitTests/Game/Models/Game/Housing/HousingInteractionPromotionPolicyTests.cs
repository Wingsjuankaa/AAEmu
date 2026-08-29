using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingInteractionPromotionPolicyTests
{
    [Test]
    public async Task ResidentialDoor_IsPromotedByItsNativeStructuralConsumers()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH4(
            10,
            AttachPointKind.HealPoint0,
            Types("DoodadFuncAnimate", "DoodadFuncTimer", "DoodadFuncUse"));

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task AdministrationPlate_IsNotSuppressedByDisabledButlerConsumer()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH4(
            10,
            AttachPointKind.NamePlate01,
            Types("DoodadFuncBindButler", "DoodadFuncCraftPack", "DoodadFuncParentInfo"));

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task ResidentialService_RemainsPendingForH5()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH4(
            10,
            AttachPointKind.Cannon0,
            Types("DoodadFuncCraftDirect", "DoodadFuncCraftPack", "DoodadFuncTimer"));

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task ResidentialCraftPack_IsPromotedInH5()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5(
            10,
            AttachPointKind.Cannon0,
            Types("DoodadFuncCraftDirect", "DoodadFuncCraftPack", "DoodadFuncTimer"),
            hasNativeCraftConsumer: true);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task CraftVisualPhaseWithoutCatalogue_RemainsBlockedInH5()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5(
            10,
            AttachPointKind.Cannon0,
            Types("DoodadFuncCraftDirect", "DoodadFuncTimer"),
            hasNativeCraftConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task QuestService_RemainsBlockedUntilItsGraphIsPromoted()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5(
            10,
            AttachPointKind.HealPoint3,
            Types("DoodadFuncQuest", "DoodadFuncRatioChange", "DoodadFuncUse"),
            hasNativeCraftConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task CraftPackWithoutMatchingStationRecipe_FailsClosedInH5()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5(
            10,
            AttachPointKind.Cannon0,
            Types("DoodadFuncCraftPack"),
            hasNativeCraftConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.MissingConsumer);
    }

    [Test]
    public async Task ProvenResidentialWaterProvider_IsPromotedInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            18,
            AttachPointKind.HealPoint3,
            Types("DoodadFuncLootItem", "DoodadFuncTimer", "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: true);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task SameWaterGraphOutsideResidentialHousing_RemainsPendingInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            33,
            AttachPointKind.HealPoint3,
            Types("DoodadFuncLootItem", "DoodadFuncTimer", "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: true);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task UnprovenLootGraph_RemainsPendingInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            18,
            AttachPointKind.HealPoint3,
            Types("DoodadFuncLootItem", "DoodadFuncTimer", "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task H5CraftPromotion_IsPreservedByH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            10,
            AttachPointKind.Cannon0,
            Types("DoodadFuncCraftDirect", "DoodadFuncCraftPack", "DoodadFuncTimer"),
            hasNativeCraftConsumer: true,
            hasNativeWaterProviderConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task MissingItemChangerConsumer_FailsClosed()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH4(
            18,
            AttachPointKind.HealPoint3,
            Types("DoodadFuncGrowth", "DoodadFuncItemChangerUiOpen", "DoodadFuncUse"));

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.MissingConsumer);
    }

    [Test]
    public async Task ProvenResidentialPlanterGraph_IsPromotedInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            18,
            AttachPointKind.HealPoint6,
            Types(
                "DoodadFuncGrowth",
                "DoodadFuncItemChanger",
                "DoodadFuncItemChangerUiOpen",
                "DoodadFuncLootPack",
                "DoodadFuncRatioChange",
                "DoodadFuncTimer",
                "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: false,
            hasNativePlanterConsumer: true);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task ProvenRancherPenGraphWithNativeFlow_IsPromotedInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            18,
            AttachPointKind.HealPoint8,
            Types(
                "DoodadFuncGrowth",
                "DoodadFuncItemChanger",
                "DoodadFuncItemChangerUiOpen",
                "DoodadFuncLootPack",
                "DoodadFuncPlayFlowGraph",
                "DoodadFuncRatioChange",
                "DoodadFuncTimer",
                "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: false,
            hasNativePlanterConsumer: true);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.None);
    }

    [Test]
    public async Task UnprovenPlanterGraph_RemainsMissingConsumerInH5B()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH5B(
            18,
            AttachPointKind.HealPoint6,
            Types("DoodadFuncGrowth", "DoodadFuncItemChangerUiOpen", "DoodadFuncUse"),
            hasNativeCraftConsumer: false,
            hasNativeWaterProviderConsumer: false,
            hasNativePlanterConsumer: false);

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.MissingConsumer);
    }

    [Test]
    public async Task DominionCategory_IsExplicitlyTerritorial()
    {
        var reason = HousingInteractionPromotionPolicy.ClassifyH4(
            19,
            AttachPointKind.HealPoint0,
            Types("DoodadFuncAnimate", "DoodadFuncTimer", "DoodadFuncUse"));

        await Assert.That(reason).IsEqualTo(HousingInteractionBlockReason.TerritorialSubsystemRequired);
    }

    private static IReadOnlySet<string> Types(params string[] values) =>
        values.ToHashSet(StringComparer.Ordinal);
}
