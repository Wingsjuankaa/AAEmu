using System;
using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Heirs
{
    /// <summary>
    /// Pure AA8 ancestral threshold policy recovered from the native heir-level consumers.
    /// </summary>
    public static class HeirProgressionPolicy
    {
        // AA8 exposes ancestral progression at the normal level cap. The active AA8
        // content and live client both identify that cap as level 55.
        public const byte StartLevel = 55;

        public static byte GetLevelForExp(IReadOnlyList<HeirLevel> levels, long totalExp)
        {
            if (levels == null || levels.Count == 0)
                return 0;

            var normalizedExp = Math.Max(0L, totalExp);
            foreach (var level in levels)
            {
                if (normalizedExp < level.ReqTotalExp)
                    return level.Level;
            }

            return levels[levels.Count - 1].Level;
        }

        public static long ApplyExpGain(
            IReadOnlyList<HeirLevel> levels,
            long totalExp,
            int expDelta)
        {
            if (levels == null || levels.Count == 0 || expDelta <= 0)
                return totalExp;

            var currentLevel = GetLevelForExp(levels, totalExp);
            var maxLevel = levels[levels.Count - 1].Level;
            if (currentLevel >= maxLevel)
                return totalExp;

            HeirLevel requirement = null;
            foreach (var level in levels)
            {
                if (level.Level == currentLevel)
                {
                    requirement = level;
                    break;
                }
            }

            if (requirement == null)
                return totalExp;

            var boundary = requirement.ReqTotalExp - 1;
            if (totalExp >= boundary)
                return boundary;

            return totalExp + Math.Min((long)expDelta, boundary - totalExp);
        }

        public static bool TryGetLevelUpRequirement(
            IReadOnlyList<HeirLevel> levels,
            byte characterLevel,
            long totalExp,
            out HeirLevel requirement)
        {
            requirement = null;
            if (levels == null || levels.Count == 0 || characterLevel < StartLevel)
                return false;

            var currentLevel = GetLevelForExp(levels, totalExp);
            if (currentLevel >= levels[levels.Count - 1].Level)
                return false;

            foreach (var level in levels)
            {
                if (level.Level == currentLevel)
                {
                    requirement = level;
                    break;
                }
            }

            return requirement != null && totalExp == requirement.ReqTotalExp - 1;
        }
    }
}
