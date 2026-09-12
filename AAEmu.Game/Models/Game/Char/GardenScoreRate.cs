namespace AAEmu.Game.Models.Game.Char;

/// <summary>User-requested, process-local GM multiplier. Does not alter saved scores or losses.</summary>
public static class GardenScoreRate
{
    public const int Maximum = 1000;
    private static int _multiplier = 1;
    public static int Multiplier => Volatile.Read(ref _multiplier);

    public static bool TrySet(int multiplier)
    {
        if (multiplier is < 1 or > Maximum)
            return false;
        Interlocked.Exchange(ref _multiplier, multiplier);
        return true;
    }

    internal static int ScaleGain(int delta) => delta <= 0 ? delta :
        (int)Math.Min((long)delta * Multiplier, int.MaxValue);
}
