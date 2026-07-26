using System;

namespace AAEmu.Commons.Models
{
    public static class CharacterSlotPolicy
    {
        public const byte DefaultMaxCharacters = 6;
        public const byte BuiltInCharacterSlots = 2;

        // AA8 ACJoinResponse `afs` is serialized as four little-endian bytes:
        // [account maximum, per-world expansion, pre-create mode, reserved].
        private const uint AccountFlagsWithoutMaximum = 0x02020400;

        public static byte NormalizeMaximum(int configuredMaximum)
        {
            if (configuredMaximum <= 0)
                return DefaultMaxCharacters;

            return (byte)Math.Min(configuredMaximum, byte.MaxValue);
        }

        public static uint BuildAccountFlags(int configuredMaximum)
        {
            return AccountFlagsWithoutMaximum | NormalizeMaximum(configuredMaximum);
        }

        public static byte GetUnlockedAdditionalSlots(int configuredMaximum)
        {
            var maximum = NormalizeMaximum(configuredMaximum);
            return maximum <= BuiltInCharacterSlots
                ? (byte)0
                : (byte)(maximum - BuiltInCharacterSlots);
        }

        public static bool CanCreate(int currentCharacters, int configuredMaximum)
        {
            return currentCharacters >= 0 &&
                   currentCharacters < NormalizeMaximum(configuredMaximum);
        }
    }
}
