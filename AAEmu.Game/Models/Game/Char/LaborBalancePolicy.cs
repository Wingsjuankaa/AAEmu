namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// Pure balance rules for the two account-scoped AA10 labor pools.
/// Persisted legacy debt is never usable labor and a spend is all-or-nothing.
/// </summary>
internal static class LaborBalancePolicy
{
    public static int NormalizeAccount(int accountLabor) => Math.Clamp(accountLabor, 0, short.MaxValue);

    public static int NormalizeLocal(int localLabor) => Math.Max(0, localLabor);

    public static int Available(int accountLabor, int localLabor) => (int)Math.Min(
        int.MaxValue,
        (long)NormalizeAccount(accountLabor) + NormalizeLocal(localLabor));

    public static bool TryPlanSpend(
        int accountLabor,
        int localLabor,
        int cost,
        out int accountDelta,
        out int localDelta)
    {
        accountDelta = 0;
        localDelta = 0;
        if (cost <= 0 || Available(accountLabor, localLabor) < cost)
            return false;

        var fromAccount = Math.Min(cost, NormalizeAccount(accountLabor));
        var fromLocal = cost - fromAccount;
        accountDelta = -fromAccount;
        localDelta = -fromLocal;
        return true;
    }
}
