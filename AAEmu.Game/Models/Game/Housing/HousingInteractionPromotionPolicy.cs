using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.Game.Models.Game.Housing;

/// <summary>
/// AA10 housing interaction promotion boundary. A proven model helper is only
/// geometry evidence; this policy decides whether the bound doodad belongs to
/// the current residential interaction wave.
/// </summary>
public static class HousingInteractionPromotionPolicy
{
    private static readonly HashSet<uint> ResidentialCategories =
    [
        1,  // house
        7,  // underwater_structure
        8,  // garden
        9,  // small_house
        10, // mid_house
        11, // large_house
        12, // mansion
        15, // floatinghouse
        16, // small_farm
        17, // farm
        18, // farmhouse
        21, // BM_farm
        22, // BM_small_house
        23, // BM_mid_house
        24, // BM_large_house
        25, // BM_mansion
        36  // expedition_house
    ];

    private static readonly HashSet<uint> TerritorialCategories =
    [
        2, 3, 4, 5, 6, 13, 14, 19, 20, 34, 35
    ];

    private static readonly HashSet<string> TerritorialFunctionTypes =
    [
        "DoodadFuncDominionCountReact",
        "DoodadFuncDominionTaxInKind",
        "DoodadFuncIssuanceOfMobilizationOrderUiOpen",
        "DoodadFuncResidentCharge"
    ];

    private static readonly HashSet<string> MissingConsumerFunctionTypes =
    [
        "DoodadFuncBindButler",
        "DoodadFuncExpeditionPortalUiOpen",
        "DoodadFuncExpeditionUiOpen",
        "DoodadFuncItemChangerUiOpen"
    ];

    public static HousingInteractionBlockReason ClassifyH4(
        uint housingCategoryId,
        AttachPointKind attachPoint,
        IReadOnlySet<string> functionTypes)
    {
        functionTypes ??= new HashSet<string>();

        if (TerritorialCategories.Contains(housingCategoryId) ||
            functionTypes.Overlaps(TerritorialFunctionTypes))
            return HousingInteractionBlockReason.TerritorialSubsystemRequired;

        if (!ResidentialCategories.Contains(housingCategoryId))
            return HousingInteractionBlockReason.PendingWavePromotion;

        var missingConsumers = functionTypes
            .Where(MissingConsumerFunctionTypes.Contains)
            .ToHashSet(StringComparer.Ordinal);

        // Butler is disabled globally until that subsystem is reconstructed.
        // It must not suppress the co-located, proven ParentInfo administration
        // consumer on AA10 nameplates.
        missingConsumers.Remove("DoodadFuncBindButler");
        if (missingConsumers.Count > 0 ||
            (functionTypes.Contains("DoodadFuncBindButler") &&
             !(attachPoint == AttachPointKind.NamePlate01 &&
               functionTypes.Contains("DoodadFuncParentInfo"))))
            return HousingInteractionBlockReason.MissingConsumer;

        var structural =
            functionTypes.Contains("DoodadFuncParentInfo") ||
            functionTypes.Contains("DoodadFuncAttachment") ||
            functionTypes.Contains("DoodadFuncClimb") ||
            functionTypes.Contains("DoodadFuncEnterSysInstance") ||
            functionTypes.Contains("DoodadFuncChangeOtherDoodadPhase") ||
            (functionTypes.Contains("DoodadFuncAnimate") &&
             functionTypes.Contains("DoodadFuncUse")) ||
            (functionTypes.Contains("DoodadFuncTod") &&
             functionTypes.Contains("DoodadFuncUse")) ||
            (attachPoint is AttachPointKind.LadderLeft or
                AttachPointKind.LadderRight or
                AttachPointKind.LadderRearLeft or
                AttachPointKind.LadderRearRight &&
             (functionTypes.Contains("DoodadFuncClimb") ||
              functionTypes.Contains("DoodadFuncFakeUse"))) ||
            (attachPoint == AttachPointKind.Driver &&
             (functionTypes.Contains("DoodadFuncUse") ||
              functionTypes.Contains("DoodadFuncLootPack")));

        return structural
            ? HousingInteractionBlockReason.None
            : HousingInteractionBlockReason.PendingWavePromotion;
    }

    /// <summary>
    /// H5 promotes the AA10 crafting catalogue consumer only after the H4
    /// residential and missing-consumer gates have passed. CraftPack is the
    /// client-visible recipe catalogue; CraftDirect/Timer only drive the
    /// station's visual phase and are not sufficient on their own.
    /// </summary>
    public static HousingInteractionBlockReason ClassifyH5(
        uint housingCategoryId,
        AttachPointKind attachPoint,
        IReadOnlySet<string> functionTypes,
        bool hasNativeCraftConsumer)
    {
        var h4 = ClassifyH4(housingCategoryId, attachPoint, functionTypes);
        if (h4 != HousingInteractionBlockReason.PendingWavePromotion)
            return h4;

        if (!functionTypes.Contains("DoodadFuncCraftPack"))
            return HousingInteractionBlockReason.PendingWavePromotion;

        return hasNativeCraftConsumer
            ? HousingInteractionBlockReason.None
            : HousingInteractionBlockReason.MissingConsumer;
    }

    /// <summary>
    /// H5-B promotes only the closed AA10 water-provider graph. The graph is
    /// proven independently in full, compact retail and compact runtime:
    /// Use (valid skill) -> LootItem (Water) -> Timer (valid next phase).
    /// Other loot, growth, quest and item-changer bindings remain closed.
    /// </summary>
    public static HousingInteractionBlockReason ClassifyH5B(
        uint housingCategoryId,
        AttachPointKind attachPoint,
        IReadOnlySet<string> functionTypes,
        bool hasNativeCraftConsumer,
        bool hasNativeWaterProviderConsumer,
        bool hasNativePlanterConsumer = false)
    {
        functionTypes ??= new HashSet<string>();
        IReadOnlySet<string> promotedFunctionTypes = functionTypes;
        if (hasNativePlanterConsumer && functionTypes.Contains("DoodadFuncItemChangerUiOpen"))
        {
            var copy = functionTypes.ToHashSet(StringComparer.Ordinal);
            copy.Remove("DoodadFuncItemChangerUiOpen");
            promotedFunctionTypes = copy;
        }

        var h5 = ClassifyH5(
            housingCategoryId,
            attachPoint,
            promotedFunctionTypes,
            hasNativeCraftConsumer);
        if (h5 != HousingInteractionBlockReason.PendingWavePromotion)
            return h5;

        // ClassifyH4 deliberately leaves unknown categories pending. H5-B must
        // not turn public/test structures into residential services merely
        // because they happen to use the same consumer graph.
        if (!ResidentialCategories.Contains(housingCategoryId))
            return HousingInteractionBlockReason.PendingWavePromotion;

        return hasNativeWaterProviderConsumer || hasNativePlanterConsumer
            ? HousingInteractionBlockReason.None
            : HousingInteractionBlockReason.PendingWavePromotion;
    }
}
