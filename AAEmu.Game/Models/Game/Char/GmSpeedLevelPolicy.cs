namespace AAEmu.Game.Models.Game.Char;

public static class GmSpeedLevelPolicy
{
    public const int MinLevel = 1;
    public const int MaxLevel = 1000;

    // AA10 game_decrypted.sqlite3 authority:
    // buffs.id=3965 has a Value modifier for MoveSpeedMul (10), value=0 and
    // linear_level_bonus=100. BuffTemplate evaluates that as AbLevel / 100,
    // so ten native ability units represent one percentage point.
    public const uint NativeBuffId = 3965;
    public const int NativeUnitsPerPercent = 10;

    public static bool IsValid(int level)
    {
        return level >= MinLevel && level <= MaxLevel;
    }

    public static uint ToNativeAbilityLevel(int level)
    {
        if (!IsValid(level))
            throw new ArgumentOutOfRangeException(nameof(level));

        return checked((uint)(level * NativeUnitsPerPercent));
    }

    public static float ToMoveSpeedMultiplier(int level)
    {
        if (!IsValid(level))
            throw new ArgumentOutOfRangeException(nameof(level));

        return 1f + level / 100f;
    }
}
