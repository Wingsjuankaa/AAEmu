using System;
using System.Linq;
using System.Numerics;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Skills.SkillControllers;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

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
        public void SavePositionBuffCapturesItsOwnersNativePosition()
        {
            var owner = new Unit();
            owner.Transform.Local.SetPosition(12f, 34f, 5f);
            owner.Transform.WorldId = 7;
            owner.Transform.InstanceId = 9;
            var template = new BuffTemplate {SavePosition = true};

            var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId),
                template, null, DateTime.UtcNow);

            Assert.Equal(new Vector3(12f, 34f, 5f), buff.SavedPosition);
            Assert.Equal(7u, buff.SavedWorldId);
            Assert.Equal(9u, buff.SavedInstanceId);
        }

        [Fact]
        public void SavePositionBuffUsesThePreMovementCastOrigin()
        {
            var owner = new Unit();
            owner.Transform.Local.SetPosition(12f, 34f, 5f);
            owner.Transform.WorldId = 7;
            owner.Transform.InstanceId = 9;
            var skill = new Skill();
            skill.CaptureCastOrigin(owner);

            owner.Transform.Local.SetPosition(90f, 80f, 70f);
            var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId),
                new BuffTemplate {SavePosition = true}, skill, DateTime.UtcNow);

            Assert.Equal(new Vector3(12f, 34f, 5f), buff.SavedPosition);
            Assert.Equal(7u, buff.SavedWorldId);
            Assert.Equal(9u, buff.SavedInstanceId);
        }

        [Fact]
        public void RegularBuffDoesNotCapturePosition()
        {
            var owner = new Unit();
            var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId),
                new BuffTemplate(), null, DateTime.UtcNow);

            Assert.Null(buff.SavedPosition);
        }

        [Fact]
        public void Aa8RootDescriptorPreventsVoluntaryMovement()
        {
            var root = new Buff(null, null, null,
                new BuffTemplate {Id = 21449, Root = true}, null, DateTime.UtcNow);
            var cosmeticFreeze = new Buff(null, null, null,
                new BuffTemplate {Id = 21450}, null, DateTime.UtcNow);

            Assert.True(Buffs.IsMovementLock(root));
            Assert.False(Buffs.IsMovementLock(cosmeticFreeze));
        }

        [Fact]
        public void ReturnToSavedPositionResolvesSameWorldMagicCircleAnchor()
        {
            var character = new Character(null);
            character.Transform.WorldId = 7;
            character.Transform.InstanceId = 9;
            character.Transform.Local.SetPosition(12f, 34f, 5f);
            var buff = new Buff(character, character, new SkillCasterUnit(character.ObjId),
                new BuffTemplate {SavePosition = true, Id = 19037}, null, DateTime.UtcNow);
            character.Transform.Local.SetPosition(90f, 80f, 70f);

            Assert.True(ReturnToSavedPosition.TryResolveDestination(
                character, buff, out var destination));
            Assert.Equal(new Vector3(12f, 34f, 5f), destination);
        }

        [Fact]
        public void ReturnToSavedPositionRejectsCrossInstanceMagicCircleAnchor()
        {
            var character = new Character(null);
            character.Transform.WorldId = 7;
            character.Transform.InstanceId = 9;
            var buff = new Buff(character, character, new SkillCasterUnit(character.ObjId),
                new BuffTemplate {SavePosition = true, Id = 19037}, null, DateTime.UtcNow);
            character.Transform.InstanceId = 10;

            Assert.False(ReturnToSavedPosition.TryResolveDestination(
                character, buff, out _));
        }

        [Fact]
        public void Aa8ForwardCuboidIncludesOnlyTargetsAlongTheForwardPath()
        {
            var origin = new Unit();
            origin.Transform.Local.SetPosition(0f, 0f, 0f);
            origin.Transform.Local.SetRotation(0f, 0f, 0f);
            var inside = UnitAt(1.9f, 6.9f, 1.9f);
            var behind = UnitAt(0f, -1f, 0f);
            var tooWide = UnitAt(2.1f, 4f, 0f);
            var tooFar = UnitAt(0f, 7.1f, 0f);
            var shape = new AreaShape
            {
                Type = AreaShapeType.ForwardCuboid,
                Value1 = 2f,
                Value2 = 7f,
                Value3 = 2f
            };

            var result = shape.ComputeForwardCuboid(origin,
                new[] {inside, behind, tooWide, tooFar}.ToList());

            Assert.Equal(new[] {inside}, result);
        }

        private static Unit UnitAt(float x, float y, float z)
        {
            var unit = new Unit();
            unit.Transform.Local.SetPosition(x, y, z);
            return unit;
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

        [Theory]
        [InlineData(WeaponWieldKind.None, 296, 299, 504, 296)]
        [InlineData(WeaponWieldKind.OneHanded, 296, 299, 504, 296)]
        [InlineData(WeaponWieldKind.TwoHanded, 296, 299, 504, 299)]
        [InlineData(WeaponWieldKind.DuelWielded, 296, 299, 504, 504)]
        [InlineData(WeaponWieldKind.TwoHanded, 296, 0, 504, 296)]
        public void FireAnimationUsesNativeWeaponVariant(WeaponWieldKind wieldKind, uint baseAnim,
            uint twohandAnim, uint dualWieldAnim, uint expected)
        {
            Assert.Equal(expected, Skill.SelectFireAnimId(wieldKind, baseAnim, twohandAnim, dualWieldAnim));
        }

        [Fact]
        public void LeapControllerAcceptsNativePositionTarget()
        {
            var owner = new Unit();
            owner.Transform.Local.SetPosition(0f, 0f, 1f);
            var positionTarget = new BaseUnit {ObjId = uint.MaxValue};
            positionTarget.Transform.Local.SetPosition(10f, 5f, 2f);
            var template = new SkillControllerTemplate
            {
                Id = 10258,
                KindId = 2, // Native AA8 SkillControllerKind.Leap
                Value = new[] {0, 1, 700, -1000, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0}
            };

            var controller = SkillController.CreateSkillController(template, owner, positionTarget);

            Assert.IsType<LeapSkillController>(controller);
            Assert.Same(positionTarget, controller.Target);
        }

        [Fact]
        public void DeadConditionTreatsPositionAsNotDead()
        {
            var condition = new PlotCondition
            {
                Kind = PlotConditionType.Dead,
                NotCondition = true
            };

            var result = condition.Check(new Unit(), null, new BaseUnit(), null, null,
                new PlotEventCondition(), null);

            Assert.True(result);
        }

        [Fact]
        public void DeadConditionAcceptsPositionAsNativePlotSource()
        {
            var condition = new PlotCondition
            {
                Kind = PlotConditionType.Dead,
                NotCondition = true
            };

            var result = condition.Check(new BaseUnit(), null, new BaseUnit(), null, null,
                new PlotEventCondition(), null);

            Assert.True(result);
        }

        [Fact]
        public void NegatedOthersRelationSelectsOnlyOriginalTarget()
        {
            var originalTarget = new Unit {ObjId = 100};
            var nearbyTarget = new Unit {ObjId = 101};
            var condition = new PlotCondition
            {
                Kind = PlotConditionType.Relation,
                Param1 = (int)SkillTargetRelation.Others,
                NotCondition = true
            };

            Assert.True(condition.Check(originalTarget, null, originalTarget, null, null,
                new PlotEventCondition(), null));
            Assert.False(condition.Check(originalTarget, null, nearbyTarget, null, null,
                new PlotEventCondition(), null));
        }

        [Fact]
        public void Aa8PositionTargetSerializesAllThreeCompressedObjectIds()
        {
            var original = new SkillCastPositionTarget
            {
                Type = SkillCastTargetType.Position,
                PosX = 14933.554f,
                PosY = 12235.029f,
                PosZ = 124.520f,
                PosRot = 0.25f,
                ObjId1 = 11,
                ObjId2 = 22,
                ObjId3 = 33
            };
            var output = new PacketStream();

            original.Write(output);

            var input = new PacketStream(output.GetBytes());
            Assert.Equal((byte)SkillCastTargetType.Position, input.ReadByte());
            var decoded = new SkillCastPositionTarget();
            decoded.Read(input);

            Assert.Equal(original.PosX, decoded.PosX, 3);
            Assert.Equal(original.PosY, decoded.PosY, 3);
            Assert.Equal(original.PosZ, decoded.PosZ, 3);
            Assert.Equal(original.PosRot, decoded.PosRot, 3);
            Assert.Equal(11u, decoded.ObjId1);
            Assert.Equal(22u, decoded.ObjId2);
            Assert.Equal(33u, decoded.ObjId3);
            Assert.False(input.HasBytes);
        }
    }
}
