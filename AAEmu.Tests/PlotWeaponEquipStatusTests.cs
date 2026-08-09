using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Plots;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotWeaponEquipStatusTests
    {
        [Theory]
        [InlineData(1, WeaponWieldKind.OneHanded)]
        [InlineData(2, WeaponWieldKind.TwoHanded)]
        [InlineData(3, WeaponWieldKind.DuelWielded)]
        public void NativeHandWeaponStatusesRetainExistingMeaning(
            int status,
            WeaponWieldKind wieldKind)
        {
            Assert.True(
                PlotCondition.MatchesWeaponEquipStatus(
                    status,
                    wieldKind,
                    false));
        }

        [Fact]
        public void NativeStatusFiveRequiresDedicatedRangedWeapon()
        {
            Assert.True(
                PlotCondition.MatchesWeaponEquipStatus(
                    (int)PlotWeaponEquipStatus.Ranged,
                    WeaponWieldKind.None,
                    true));
            Assert.False(
                PlotCondition.MatchesWeaponEquipStatus(
                    (int)PlotWeaponEquipStatus.Ranged,
                    WeaponWieldKind.DuelWielded,
                    false));
        }

        [Fact]
        public void UnknownNativeStatusFailsClosed()
        {
            Assert.False(
                PlotCondition.MatchesWeaponEquipStatus(
                    4,
                    WeaponWieldKind.OneHanded,
                    true));
        }
    }
}
