using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.Game.Models.Game.Crafts;

/// <summary>
/// Pure AA10 Wave 1 station gate. Permission modes other than Public remain closed until their
/// native ownership contracts are demonstrated.
/// </summary>
public static class CraftStationValidator
{
    public static bool TryValidate(
        Craft craft,
        bool stationExists,
        uint stationTemplateId,
        DoodadFuncPermission? permission,
        out CraftFailure failure)
    {
        failure = CraftFailure.None;
        if (craft is null)
        {
            failure = new CraftFailure(CraftFailureCode.RecipeUnavailable);
            return false;
        }

        if (craft.ReqDoodadId != 0 &&
            (!stationExists || stationTemplateId != craft.ReqDoodadId))
        {
            failure = new CraftFailure(CraftFailureCode.StationUnavailable);
            return false;
        }

        if (stationExists && permission != DoodadFuncPermission.Public)
        {
            failure = new CraftFailure(CraftFailureCode.PermissionDenied);
            return false;
        }

        return true;
    }
}
