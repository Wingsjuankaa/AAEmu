using System;
using System.Numerics;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills.SkillControllers;

using Xunit;

namespace AAEmu.Tests
{
    public class SkillMovementTests
    {
        [Fact]
        public void SelfTargetLeapUsesOwnerFacing()
        {
            var origin = new Vector3(10f, 20f, 3f);

            var destination = LeapSkillController.CalculateEndPosition(origin, origin, 0f, 5000);

            Assert.Equal(new Vector3(10f, 25f, 3f), destination);
        }

        [Fact]
        public void TargetedLeapAppliesOffsetFromTarget()
        {
            var destination = LeapSkillController.CalculateEndPosition(
                Vector3.Zero, new Vector3(10f, 0f, 2f), 0f, -800);

            Assert.Equal(9.2f, destination.X, 3);
            Assert.Equal(0f, destination.Y, 3);
            Assert.Equal(2f, destination.Z, 3);
        }

        [Fact]
        public void UnitBlinkUsesConfirmedAa8WireLayout()
        {
            var stream = new PacketStream();
            new SCUnitBlinkPacket(7, 15f, 0f, true, 1f, 2f, 3f).Write(stream);

            var bytes = stream.GetBytes();
            Assert.Equal(32, bytes.Length);
            Assert.Equal(1, bytes[11]);
            Assert.Equal(3f, BitConverter.ToSingle(bytes, 28));
        }
    }
}
