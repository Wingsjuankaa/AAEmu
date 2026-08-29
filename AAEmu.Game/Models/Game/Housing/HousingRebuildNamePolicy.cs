namespace AAEmu.Game.Models.Game.Housing;

/// <summary>
/// Preserves player-authored house names while replacing a source template's
/// default name with the target template's native localized name.
/// </summary>
public static class HousingRebuildNamePolicy
{
    public static string ResolveTransition(
        string currentName,
        string sourceDefaultName,
        string targetDefaultName)
    {
        if (string.IsNullOrWhiteSpace(targetDefaultName))
            return currentName ?? string.Empty;

        return string.IsNullOrWhiteSpace(currentName) ||
               string.Equals(currentName, sourceDefaultName, StringComparison.Ordinal)
            ? targetDefaultName
            : currentName;
    }

    public static string ResolveLoadedLegacyDefault(
        string currentName,
        string targetDefaultName,
        IReadOnlySet<string> incomingSourceDefaultNames)
    {
        if (string.IsNullOrWhiteSpace(targetDefaultName))
            return currentName ?? string.Empty;
        if (string.IsNullOrWhiteSpace(currentName))
            return targetDefaultName;
        if (string.Equals(currentName, targetDefaultName, StringComparison.Ordinal))
            return currentName;

        return incomingSourceDefaultNames?.Contains(currentName) == true
            ? targetDefaultName
            : currentName;
    }
}
