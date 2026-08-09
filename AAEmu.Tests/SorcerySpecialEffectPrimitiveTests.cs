using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Interactions;
using System.Numerics;
using Xunit;

namespace AAEmu.Tests
{
    public class SorcerySpecialEffectPrimitiveTests
    {
        [Theory]
        [InlineData(0, 99, true)]
        [InlineData(100, 99, true)]
        [InlineData(25, 24, true)]
        [InlineData(25, 25, false)]
        public void SkillUseChance_UsesAa8PercentBoundary(
            int chance, int roll, bool expected)
        {
            Assert.Equal(expected, SkillUse.PassesChance(chance, roll));
        }

        [Theory]
        [InlineData(0, 99, true)]
        [InlineData(100, 99, true)]
        [InlineData(25, 24, true)]
        [InlineData(25, 25, false)]
        public void DisturbCastingChance_UsesAa8PercentBoundary(
            int chance, int roll, bool expected)
        {
            Assert.Equal(expected, DisturbCasting.PassesChance(chance, roll));
        }

        [Fact]
        public void SkillUseSelfTarget_DoesNotReuseCurrentTarget()
        {
            var caster = new Unit { ObjId = 100 };
            var selectedEnemy = new Unit { ObjId = 200 };
            caster.CurrentTarget = selectedEnemy;

            var result = SkillUse.BuildTarget(
                SkillTargetType.Self,
                caster,
                new SkillCastUnitTarget(selectedEnemy.ObjId));

            var unitTarget = Assert.IsType<SkillCastUnitTarget>(result);
            Assert.Equal(caster.ObjId, unitTarget.ObjId);
        }

        [Fact]
        public void SkillUseHostileTarget_PreservesTriggeredUnit()
        {
            var triggeredTarget = new Unit { ObjId = 300 };

            var result = SkillUse.BuildTarget(
                SkillTargetType.Hostile,
                triggeredTarget,
                new SkillCastUnitTarget(999));

            var unitTarget = Assert.IsType<SkillCastUnitTarget>(result);
            Assert.Equal(triggeredTarget.ObjId, unitTarget.ObjId);
        }

        [Fact]
        public void FireWallMistSkillUse_PreservesTheTimedWallAnchorPosition()
        {
            var wallAnchor = new Unit { ObjId = 400 };
            wallAnchor.Transform.Local.SetPosition(123.5f, 456.25f, 7.75f, 0f, 0f, 1.25f);
            var staleCursor = new SkillCastPositionTarget
            {
                Type = SkillCastTargetType.Position,
                PosX = -1f,
                PosY = -2f,
                PosZ = -3f
            };

            var result = SkillUse.BuildTarget(
                SkillTargetType.Pos,
                wallAnchor,
                staleCursor);

            var position = Assert.IsType<SkillCastPositionTarget>(result);
            Assert.Equal(123.5f, position.PosX);
            Assert.Equal(456.25f, position.PosY);
            Assert.Equal(7.75f, position.PosZ);
        }

        [Fact]
        public void MeteorPrimaryKnockBackUsesAa8MagnitudeAndElevation()
        {
            var displacement = ForcedMovementEffectCalculator.CalculateKnockBackDisplacement(
                Vector3.Zero, Vector3.UnitX, 1400, 75);

            Assert.Equal(0.362f, displacement.X, 3);
            Assert.Equal(0f, displacement.Y, 3);
            Assert.Equal(1.352f, displacement.Z, 3);
        }

        [Fact]
        public void MeteorSecondaryKnockBackPreservesNegativeElevation()
        {
            var displacement = ForcedMovementEffectCalculator.CalculateKnockBackDisplacement(
                Vector3.Zero, Vector3.UnitY, 400, -15);

            Assert.Equal(0f, displacement.X, 3);
            Assert.Equal(0.386f, displacement.Y, 3);
            Assert.Equal(-0.104f, displacement.Z, 3);
        }

        [Theory]
        [InlineData(0f, 100f)]
        [InlineData(1f, 100f)]
        [InlineData(4.999f, 100f)]
        [InlineData(5f, 100f)]
        [InlineData(5.001f, 0f)]
        public void PhysicalExplosionUsesCryEngineConstantPressureEnvelope(float distance, float expected)
        {
            Assert.Equal(expected,
                ForcedMovementEffectCalculator.CalculateExplosionPressure(distance, 5f, 100f));
        }

        [Fact]
        public void SummonDoodadSourceDirectionUsesTheCasterOrientation()
        {
            var targetRotation = new Vector3(1f, 2f, 3f);
            var sourceRotation = new Vector3(4f, 5f, 6f);

            Assert.Equal(sourceRotation,
                SummonDoodad.ResolveSummonedRotation(targetRotation, sourceRotation, true));
            Assert.Equal(targetRotation,
                SummonDoodad.ResolveSummonedRotation(targetRotation, sourceRotation, false));
        }
    }
}
