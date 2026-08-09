using System;

namespace AAEmu.Game.Models.Game.Char
{
    public static class GmSpeedLevelPolicy
    {
        public const int MinLevel = 1;
        public const int MaxLevel = 1000;

        // AA8 compact authority:
        // buffs.id=3965 ("set item_move speed") has one Value modifier for
        // UnitAttribute.MoveSpeedMul (10), value=0 and linear_level_bonus=100.
        // The native formula therefore makes AbLevel equal the raw modifier.
        public const uint NativeBuffId = 3965;
        public const int NativeUnitsPerPercent = 10;

        public static bool IsValid(int level)
        {
            return level >= MinLevel && level <= MaxLevel;
        }

        public static ushort ToNativeAbilityLevel(int level)
        {
            if (!IsValid(level))
                throw new ArgumentOutOfRangeException(nameof(level));

            return checked((ushort)(level * NativeUnitsPerPercent));
        }

        public static float ToMoveSpeedMultiplier(int level)
        {
            if (!IsValid(level))
                throw new ArgumentOutOfRangeException(nameof(level));

            return 1f + level / 100f;
        }
    }
}
