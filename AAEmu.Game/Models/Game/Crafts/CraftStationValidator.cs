using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.Game.Models.Game.Crafts;

/// <summary>
/// Pure AA10 crafting station gate. Active CraftPack membership proves alternative stations;
/// Tax certificates offered by a public nameplate function do not require parcel access.
/// All other recipes retain both function and parcel permission gates.
/// </summary>
public static class CraftStationValidator
{
    public static bool TryValidate(
        Craft craft,
        bool stationExists,
        uint stationTemplateId,
        DoodadFuncPermission? permission,
        out CraftFailure failure,
        IEnumerable<CraftStationOffer> activeOffers = null,
        bool housingAccessAllowed = true)
    {
        failure = CraftFailure.None;
        if (craft is null)
        {
            failure = new CraftFailure(CraftFailureCode.RecipeUnavailable);
            return false;
        }

        var matchingOffers = activeOffers?
            .Where(offer => offer.CraftPackId != 0 && craft.CraftPackIds.Contains(offer.CraftPackId))
            .ToArray() ?? [];
        if (craft.ReqDoodadId != 0 &&
            (!stationExists || (stationTemplateId != craft.ReqDoodadId && matchingOffers.Length == 0)))
        {
            failure = new CraftFailure(CraftFailureCode.StationUnavailable);
            return false;
        }

        // Check the matching crafting function, not an unrelated first function (e.g. Butler).
        // Unproven non-public function modes remain fail-closed even on an accessible parcel.
        var functionAllowed = matchingOffers.Length > 0
            ? matchingOffers.Any(offer => offer.Permission == DoodadFuncPermission.Public)
            : permission == DoodadFuncPermission.Public;
        // r575 full + retail: nameplate catalogue 3 contains only tax recipes 76/9267,
        // both requiring canonical nameplate 2392. Taxes are public even on private land.
        // Require the exact live public offer; a recipe ID, generic Public callback or
        // canonical template alone must never grant this exception (including after a phase change).
        // See CHECKPOINT_HOUSING_TAX_CRAFT_STATION_20260903.md, cross-account correction.
        var publicTaxOffer = craft.Id is 76 or 9267 && craft.ReqDoodadId == 2392 &&
            matchingOffers.Any(offer => offer.CraftPackId == 3 &&
                                        offer.Permission == DoodadFuncPermission.Public);
        if (stationExists && (!functionAllowed || (!housingAccessAllowed && !publicTaxOffer)))
        {
            failure = new CraftFailure(CraftFailureCode.PermissionDenied);
            return false;
        }

        return true;
    }
}

public readonly record struct CraftStationOffer(uint CraftPackId, DoodadFuncPermission Permission);
