using System;

using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Utils;

using Xunit;

namespace AAEmu.Tests
{
    public class FrontArcTests
    {
        [Theory]
        [InlineData(0f, 1f, true)]
        [InlineData(0f, -1f, false)]
        [InlineData(1f, 0f, true)]
        [InlineData(-1f, 0f, true)]
        public void IsFrontUsesObserverFacing(float subjectX, float subjectY, bool expected)
        {
            var observer = CreateObject(0f, 0f, 0f);
            var subject = CreateObject(subjectX, subjectY, 0f);

            Assert.Equal(expected, MathUtil.IsFront(subject, observer));
        }

        [Fact]
        public void IsFrontNormalizesAcrossNegativeAndPositive180Degrees()
        {
            var observer = CreateObject(0f, 0f, 100f);
            var subject = CreateObject(
                MathF.Cos(-170f.DegToRad()),
                MathF.Sin(-170f.DegToRad()),
                0f);

            Assert.True(MathUtil.IsFront(subject, observer));
            Assert.InRange(MathUtil.CalculateRelativeAngle(observer, subject), -0.001, 0.001);
        }

        [Fact]
        public void IsFrontComparesDegreesWithRadianYawCorrectly()
        {
            var observer = CreateObject(0f, 0f, 90f);
            var subject = CreateObject(-1f, 0f, 0f);

            Assert.True(MathUtil.IsFront(subject, observer));
        }

        private static GameObject CreateObject(float x, float y, float yawDegrees)
        {
            var gameObject = new GameObject();
            gameObject.Transform.Local.SetPosition(x, y, 0f);
            gameObject.Transform.Local.SetRotationDegree(0f, 0f, yawDegrees);
            return gameObject;
        }
    }
}
