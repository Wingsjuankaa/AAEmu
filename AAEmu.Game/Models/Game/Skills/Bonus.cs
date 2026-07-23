using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.Game.Models.Game.Skills
{
    public class Bonus
    {
        public BonusTemplate Template { get; set; }
        public int Value { get; set; }

        public static int ToRuntimeValue(long nativeValue)
        {
            // The compact/template keeps the exact signed 64-bit AA8 value.
            // Legacy Unit properties are 32-bit, so saturation is the only
            // safe boundary until those properties are migrated.
            if (nativeValue > int.MaxValue)
                return int.MaxValue;
            if (nativeValue < int.MinValue)
                return int.MinValue;
            return (int)nativeValue;
        }
    }
}
