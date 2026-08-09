using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using Xunit;

namespace AAEmu.Tests
{
    public class SorceryDamageEffectTests
    {
        [Fact]
        public void NativeBaseDamage_AddsFixedLevelAndDpsBeforeMultipliers()
        {
            var result = DamageEffectCalculator.CalculateBaseDamageRange(
                useFixedDamage: true,
                fixedMin: 10,
                fixedMax: 20,
                useLevelDamage: true,
                levelDps: 100f,
                abilityLevel: 50,
                requiredAbilityLevel: 10,
                castingInc: 10,
                levelMd: 2f,
                levelVaStart: 5,
                levelVaEnd: 15,
                dpsStat: 100000,
                dpsIncMultiplier: 2f,
                weaponDps: 0,
                dpsMultiplier: 0f,
                castingTime: 2000,
                weaponDamageScale: 0,
                descriptorMultiplier: 1.5f,
                globalDamageMultiplier: 1.1f);

            Assert.Equal(1333, result.Min);
            Assert.Equal(1488, result.Max);
        }

        [Fact]
        public void WeaponDamageScale_ProducesSymmetricNativeRange()
        {
            var result = DamageEffectCalculator.CalculateBaseDamageRange(
                false, 0, 0, false, 0f, 1, 1, 0, 0f, 0, 0,
                0, 0f, 100000, 1f, 1000, 10, 1f, 1f);

            Assert.Equal(90, result.Min);
            Assert.Equal(110, result.Max);
        }

        [Theory]
        [InlineData(0.99f, 1f)]
        [InlineData(1f, 1.06f)]
        [InlineData(10f, 1.15f)]
        [InlineData(150f, 2.05f)]
        public void HeightMultiplier_MatchesAa8Formula11(float height, float expected)
        {
            Assert.Equal(expected,
                DamageEffectCalculator.CalculateHeightMultiplier(height), 3);
        }

        [Theory]
        [InlineData(0f, 1f)]
        [InlineData(5f, 1.25f)]
        [InlineData(10f, 2f)]
        [InlineData(15f, 1.25f)]
        [InlineData(20f, 1f)]
        public void RangeMultiplier_MatchesAa8Formula12(float range, float expected)
        {
            Assert.Equal(expected,
                DamageEffectCalculator.CalculateRangeMultiplier(range, 10f, 2f), 3);
        }

        [Fact]
        public void AoeDiminishing_ReachesFiftyPercentFloorAtEleventhTarget()
        {
            var context = new AoeDiminishingContext();
            Assert.Equal(1f, context.GetOrAssignMultiplier(100), 3);
            Assert.Equal(1f, context.GetOrAssignMultiplier(100), 3);
            for (uint id = 101; id < 110; id++)
                context.GetOrAssignMultiplier(id);
            Assert.Equal(0.5f, context.GetOrAssignMultiplier(110), 3);
            Assert.Equal(0.5f, context.GetOrAssignMultiplier(111), 3);

            context.Reset();
            Assert.Equal(1f, context.GetOrAssignMultiplier(111), 3);
        }

        [Fact]
        public void AggroLevelBranch_UsesCurrentAbilityLevelAndRankScale()
        {
            var result = AggroEffectCalculator.CalculateBaseAggroRange(
                false, 0, 0,
                true, 100f,
                abilityLevel: 50,
                requiredAbilityLevel: 10,
                castingInc: 10,
                levelMd: 0.5f,
                levelVaStart: 10,
                levelVaEnd: 20);

            Assert.Equal(56, result.Min);
            Assert.Equal(84, result.Max);
        }
    }
}
