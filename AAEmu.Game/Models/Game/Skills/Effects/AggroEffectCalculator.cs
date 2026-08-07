using System;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// Deterministic AA8 aggro range construction. The level branch uses
    /// the caster's current specialization level; Skill.Level is the row
    /// rank and is not the native input for level variance.
    /// </summary>
    public static class AggroEffectCalculator
    {
        public static (int Min, int Max) CalculateBaseAggroRange(
            bool useFixedAggro,
            int fixedMin,
            int fixedMax,
            bool useLevelAggro,
            float levelDps,
            int abilityLevel,
            int requiredAbilityLevel,
            int castingInc,
            float levelMd,
            int levelVaStart,
            int levelVaEnd)
        {
            var min = useFixedAggro ? fixedMin : 0;
            var max = useFixedAggro ? fixedMax : 0;

            if (useLevelAggro)
            {
                var rankScale = DamageEffectCalculator.CalculateRankScale(
                    abilityLevel,
                    requiredAbilityLevel,
                    castingInc);
                var levelBase = levelDps * (rankScale + 1f) * levelMd;
                var variation = (((abilityLevel - 1f) / 49f)
                    * (levelVaEnd - levelVaStart) + levelVaStart) * 0.01f;
                min += (int)(levelBase - variation * levelBase + 0.5f);
                max += (int)((variation + 1f) * levelBase + 0.5f);
            }

            return min <= max ? (min, max) : (max, min);
        }
    }
}
