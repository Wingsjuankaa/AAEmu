namespace AAEmu.Game.Models.Game.Housing;

/// <summary>
/// Pure AA10 housing-principal policy. Runtime lookups (family and expedition)
/// are resolved by <see cref="House"/> and passed here as facts so every entry
/// point applies the same permission matrix.
/// </summary>
public static class HousingAccessPolicy
{
    public static bool Allows(
        HousingPermission permission,
        bool alwaysPublic,
        bool unfinished,
        uint ownerId,
        uint ownerAccountId,
        uint characterId,
        uint characterAccountId,
        bool sameFamily,
        bool sameGuild)
    {
        if (alwaysPublic || unfinished)
            return true;

        // AA grants land access to every character on the owning account.
        // This applies even while the displayed permission is Private.
        if (characterId == ownerId ||
            (ownerAccountId != 0 && characterAccountId == ownerAccountId))
            return true;

        return permission switch
        {
            HousingPermission.Family => sameFamily,
            HousingPermission.Guild => sameGuild,
            HousingPermission.Public => true,
            HousingPermission.Private => false,
            _ => false
        };
    }
}
