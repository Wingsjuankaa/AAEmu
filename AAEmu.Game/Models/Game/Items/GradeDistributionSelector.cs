using System;
using System.Linq;

namespace AAEmu.Game.Models.Game.Items
{
    /// <summary>
    /// Resolves the native AA8 item-grade distribution.
    /// AA8 stores weights for grades 0 through 12 and does not require
    /// the sum to use an assumed percentage scale.
    /// </summary>
    public static class GradeDistributionSelector
    {
        public static int GetTotalWeight(GradeDistributions distribution)
        {
            if (distribution == null)
                throw new ArgumentNullException(nameof(distribution));

            return distribution.Weights.Where(weight => weight > 0).Sum();
        }

        public static byte SelectByRoll(GradeDistributions distribution, int roll)
        {
            var totalWeight = GetTotalWeight(distribution);
            if (totalWeight <= 0)
                throw new InvalidOperationException(
                    $"Grade distribution {distribution.Id} has no positive weights");
            if (roll < 0 || roll >= totalWeight)
                throw new ArgumentOutOfRangeException(
                    nameof(roll), roll, $"Roll must be between 0 and {totalWeight - 1}");

            var cumulative = 0;
            var weights = distribution.Weights;
            for (byte grade = 0; grade < weights.Length; grade++)
            {
                var weight = weights[grade];
                if (weight <= 0)
                    continue;

                cumulative += weight;
                if (roll < cumulative)
                    return grade;
            }

            throw new InvalidOperationException(
                $"Grade distribution {distribution.Id} could not resolve roll {roll}");
        }
    }
}
