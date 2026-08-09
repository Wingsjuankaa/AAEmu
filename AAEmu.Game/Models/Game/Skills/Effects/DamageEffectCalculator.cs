using System;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// Deterministic AA8 damage primitives recovered from the native client and
    /// the formulas table in the Kakao 8.0.3.12 compact database.
    /// </summary>
    public static class DamageEffectCalculator
    {
        public static (int Min, int Max) CalculateBaseDamageRange(
            bool useFixedDamage,
            int fixedMin,
            int fixedMax,
            bool useLevelDamage,
            float levelDps,
            int abilityLevel,
            int requiredAbilityLevel,
            int castingInc,
            float levelMd,
            int levelVaStart,
            int levelVaEnd,
            int dpsStat,
            float dpsIncMultiplier,
            int weaponDps,
            float dpsMultiplier,
            int castingTime,
            int weaponDamageScale,
            float descriptorMultiplier,
            float globalDamageMultiplier,
            float equipmentDamageMultiplier = 1f)
        {
            var min = useFixedDamage ? fixedMin : 0;
            var max = useFixedDamage ? fixedMax : 0;

            var rankScale = CalculateRankScale(
                abilityLevel,
                requiredAbilityLevel,
                castingInc);

            if (useLevelDamage)
            {
                var levelBase = levelDps * (rankScale + 1f) * levelMd;
                var variation = (((abilityLevel - 1f) / 49f)
                    * (levelVaEnd - levelVaStart) + levelVaStart) * 0.01f;
                min += (int)(levelBase - variation * levelBase + 0.5f);
                max += (int)((variation + 1f) * levelBase + 0.5f);
            }

            var effectiveCastingTime = Math.Max(
                1000,
                (int)(castingTime * (rankScale + 1f)));
            var dpsDamage = (int)(effectiveCastingTime
                * (dpsStat * 0.001f * dpsIncMultiplier
                    + weaponDps * 0.001f * dpsMultiplier)
                * 0.001f);

            if (weaponDamageScale > 0)
            {
                var variance = weaponDamageScale * dpsDamage * 0.01f;
                min += (int)(dpsDamage - variance);
                max += (int)(dpsDamage + variance);
            }
            else
            {
                min += dpsDamage;
                max += dpsDamage;
            }

            min = (int)(min * descriptorMultiplier);
            max = (int)(max * descriptorMultiplier);
            min = (int)(min * globalDamageMultiplier);
            max = (int)(max * globalDamageMultiplier);
            min = (int)(min * equipmentDamageMultiplier);
            max = (int)(max * equipmentDamageMultiplier);

            return min <= max ? (min, max) : (max, min);
        }

        public static float CalculateRankScale(
            int abilityLevel,
            int requiredAbilityLevel,
            int castingInc)
        {
            return Math.Max(0, abilityLevel - requiredAbilityLevel)
                * castingInc * 0.001f;
        }

        /// <summary>
        /// AA8 formulas.id=11. The input is the positive vertical separation
        /// between source and target in metres.
        /// </summary>
        public static float CalculateHeightMultiplier(float heightDifference)
        {
            if (heightDifference < 1f)
                return 1f;
            return 1.05f + Math.Min(heightDifference, 100f) / 100f;
        }

        /// <summary>
        /// AA8 formulas.id=12.
        /// </summary>
        public static float CalculateRangeMultiplier(
            float distance,
            float optimumRange,
            float rangeDamageMultiplier)
        {
            if (optimumRange <= 0f || distance >= optimumRange * 2f)
                return 1f;

            var delta = rangeDamageMultiplier - 1f;
            if (distance < optimumRange)
                return delta / (optimumRange * optimumRange)
                    * distance * distance + 1f;

            var fromFarEdge = distance - optimumRange * 2f;
            return delta / (optimumRange * optimumRange)
                * fromFarEdge * fromFarEdge + 1f;
        }

        public static float CalculateAoeDiminishingMultiplier(int targetIndex)
        {
            return Math.Max(0.5f, 1f - Math.Max(0, targetIndex) * 0.05f);
        }
    }
}
