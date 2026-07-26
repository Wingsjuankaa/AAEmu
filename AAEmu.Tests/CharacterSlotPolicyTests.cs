using AAEmu.Commons.Models;
using Xunit;

namespace AAEmu.Tests
{
    public class CharacterSlotPolicyTests
    {
        [Fact]
        public void DefaultMaximumAllowsThirdCharacter()
        {
            Assert.True(CharacterSlotPolicy.CanCreate(2, CharacterSlotPolicy.DefaultMaxCharacters));
            Assert.False(CharacterSlotPolicy.CanCreate(6, CharacterSlotPolicy.DefaultMaxCharacters));
        }

        [Fact]
        public void AccountFlagsAdvertiseConfiguredMaximumWithoutChangingOtherAa8Fields()
        {
            Assert.Equal(0x02020406u, CharacterSlotPolicy.BuildAccountFlags(6));
        }

        [Theory]
        [InlineData(2, 0)]
        [InlineData(3, 1)]
        [InlineData(6, 4)]
        public void AdditionalSlotsUnlockEverythingBeyondTheTwoBuiltInSlots(
            int configuredMaximum,
            byte expectedAdditionalSlots)
        {
            Assert.Equal(
                expectedAdditionalSlots,
                CharacterSlotPolicy.GetUnlockedAdditionalSlots(configuredMaximum));
        }

        [Theory]
        [InlineData(0)]
        [InlineData(-1)]
        public void InvalidConfigurationFallsBackToDefault(int configuredMaximum)
        {
            Assert.Equal(
                CharacterSlotPolicy.DefaultMaxCharacters,
                CharacterSlotPolicy.NormalizeMaximum(configuredMaximum));
        }
    }
}
