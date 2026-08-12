using System.Reflection;
using AAEmu.Game.Models.Game.Transfers;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Transform;
using Xunit;

namespace AAEmu.Tests
{
    public class TransferLifecycleTests
    {
        [Fact]
        public void BoundedTransferStartsOnRouteAndFollowsMotorWithoutParentInversion()
        {
            var motor = new Transfer();
            var boardingPart = new Transfer();
            motor.Bounded = boardingPart;
            motor.Transform.ApplyWorldSpawnPosition(new WorldSpawnPosition
            {
                WorldId = 1,
                ZoneId = 99,
                X = 10f,
                Y = 20f,
                Z = 30f
            });
            boardingPart.Transform.StickyParent = motor.Transform;
            boardingPart.Transform.ApplyWorldSpawnPosition(new WorldSpawnPosition
            {
                WorldId = 1,
                ZoneId = 99,
                X = 10f,
                Y = 20f,
                Z = 30f
            }, keepStickyParent: true);

            var routeStart = new WorldSpawnPosition
            {
                WorldId = 1,
                ZoneId = 99,
                X = 100f,
                Y = 200f,
                Z = 300f,
                Yaw = 0f
            };
            var align = typeof(TransferSpawner).GetMethod(
                "AlignBoundedAtRouteStart",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(align);
            align.Invoke(null, new object[] { motor, routeStart });

            Assert.Equal(routeStart.WorldId, boardingPart.Transform.WorldId);
            Assert.Equal(routeStart.ZoneId, boardingPart.Transform.ZoneId);
            Assert.Equal(routeStart.X, boardingPart.Transform.Local.Position.X, 3);
            Assert.Equal(
                routeStart.Y + Transfer.BoundedChildAlongFrontOffsetMeters,
                boardingPart.Transform.Local.Position.Y,
                3);
            Assert.Equal(routeStart.Z, boardingPart.Transform.Local.Position.Z, 3);
            Assert.Null(motor.Transform.Parent);
            Assert.Null(boardingPart.Transform.Parent);
            Assert.Same(motor.Transform, boardingPart.Transform.StickyParent);

            motor.Transform.ApplyWorldSpawnPosition(routeStart, keepStickyParent: true);
            motor.Transform.ResetFinalizeTransform();
            var boardingBeforeMove = boardingPart.Transform.World.ClonePosition();
            var movement = new System.Numerics.Vector3(5f, -2f, 1f);

            motor.Transform.Local.Translate(movement);
            motor.Transform.FinalizeTransform();

            Assert.Equal(
                boardingBeforeMove.X + movement.X,
                boardingPart.Transform.World.Position.X,
                3);
            Assert.Equal(
                boardingBeforeMove.Y + movement.Y,
                boardingPart.Transform.World.Position.Y,
                3);
            Assert.Equal(
                boardingBeforeMove.Z + movement.Z,
                boardingPart.Transform.World.Position.Z,
                3);
        }
    }
}
