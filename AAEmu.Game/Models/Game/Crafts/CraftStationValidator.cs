using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.Game.Models.Game.Crafts;

/// <summary>
/// Pure AA10 crafting station gate. Active CraftPack membership proves alternative stations;
/// catalogue access does not bypass function or parcel permissions.
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
        if (stationExists && (!housingAccessAllowed || !functionAllowed))
        {
            failure = new CraftFailure(CraftFailureCode.PermissionDenied);
            return false;
        }

        return true;
    }
}

public readonly record struct CraftStationOffer(uint CraftPackId, DoodadFuncPermission Permission);
