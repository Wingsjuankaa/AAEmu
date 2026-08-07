using System.Collections.Generic;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;

using Xunit;

namespace AAEmu.Tests
{
    public class PlotCombatDiceResultTests
    {
        public static IEnumerable<object[]> NativeResultCases()
        {
            yield return new object[] { 1, SkillHitType.MeleeHit };
            yield return new object[] { 1, SkillHitType.RangedHit };
            yield return new object[] { 1, SkillHitType.SpellHit };
            yield return new object[] { 2, SkillHitType.MeleeCritical };
            yield return new object[] { 2, SkillHitType.RangedCritical };
            yield return new object[] { 2, SkillHitType.SpellCritical };
            yield return new object[] { 3, SkillHitType.MeleeMiss };
            yield return new object[] { 3, SkillHitType.RangedMiss };
            yield return new object[] { 3, SkillHitType.SpellMiss };
            yield return new object[] { 4, SkillHitType.MeleeDodge };
            yield return new object[] { 4, SkillHitType.RangedDodge };
            yield return new object[] { 5, SkillHitType.MeleeBlock };
            yield return new object[] { 5, SkillHitType.RangedBlock };
            yield return new object[] { 6, SkillHitType.MeleeParry };
            yield return new object[] { 6, SkillHitType.RangedParry };
            yield return new object[] { 7, SkillHitType.SpellResist };
            yield return new object[] { 8, SkillHitType.Immune };
        }

        [Theory]
        [MemberData(nameof(NativeResultCases))]
        public void SingleNativeBitMatchesOnlyItsResult(int resultId, SkillHitType hitType)
        {
            var mask = 1 << (resultId - 1);

            Assert.True(PlotCondition.MatchesCombatDiceResult(mask, hitType));
            Assert.False(PlotCondition.MatchesCombatDiceResult(mask ^ 0xff, hitType));
        }

        [Theory]
        [InlineData(SkillHitType.MeleeHit, true)]
        [InlineData(SkillHitType.SpellCritical, true)]
        [InlineData(SkillHitType.MeleeBlock, true)]
        [InlineData(SkillHitType.RangedParry, true)]
        [InlineData(SkillHitType.SpellMiss, false)]
        [InlineData(SkillHitType.RangedDodge, false)]
        [InlineData(SkillHitType.SpellResist, false)]
        [InlineData(SkillHitType.Immune, false)]
        public void FreezingEarthMask51MatchesNativeSuccessEnvelope(
            SkillHitType hitType,
            bool expected)
        {
            Assert.Equal(
                expected,
                PlotCondition.MatchesCombatDiceResult(51, hitType));
        }

        [Fact]
        public void InvalidHitTypeNeverMatches()
        {
            Assert.False(PlotCondition.MatchesCombatDiceResult(255, SkillHitType.Invalid));
        }

        [Theory]
        [InlineData(0, 0, 0, false)]
        [InlineData(1, 0, 0, true)]
        [InlineData(1, 1, 1, true)]
        [InlineData(2, 1, 1, false)]
        [InlineData(3, 2, 4, true)]
        [InlineData(5, 2, 4, false)]
        public void NativeBuffTagStackEnvelopeHonorsParam3AndParam4(
            int stack,
            int minimum,
            int maximum,
            bool expected)
        {
            Assert.Equal(
                expected,
                PlotCondition.MatchesBuffStackRange(stack, minimum, maximum));
        }
    }
}
