using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;

using Xunit;

namespace AAEmu.Tests
{
    public class QuestAvailabilityGuardTests
    {
        [Theory]
        [InlineData(10, (byte)Race.Nuian, 1, 19, 1, true, "")]
        [InlineData(10, (byte)Race.Elf, 1, 19, 8, true, "")]
        [InlineData(10, (byte)Race.Elf, 1, 19, 1, false, "race_not_allowed")]
        [InlineData(10, (byte)Race.Warborn, 1, 19, 128, true, "")]
        [InlineData(10, (byte)Race.Ferre, 1, 19, 255, true, "")]
        [InlineData(10, (byte)Race.Ferre, 1, 19, 0, true, "")]
        [InlineData(2, (byte)Race.Nuian, 3, 19, 255, false, "below_min_level")]
        [InlineData(20, (byte)Race.Nuian, 1, 19, 255, false, "above_max_level")]
        public void EvaluateHonorsNativeLevelAndRaceMask(
            byte level,
            byte race,
            byte minLevel,
            byte maxLevel,
            byte raceMask,
            bool expected,
            string expectedReason)
        {
            var result = QuestAvailabilityGuard.Evaluate(
                level,
                race,
                minLevel,
                maxLevel,
                raceMask,
                out var reason);

            Assert.Equal(expected, result);
            Assert.Equal(expectedReason, reason);
        }
    }
}
