using System;
using System.Collections.Generic;
using System.Numerics;
using System.Text;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Movements;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Utils;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.SkillControllers
{
    public class LeapSkillController : SkillController
    {
        private static readonly Logger _log = LogManager.GetCurrentClassLogger();

        public int Angle { get; set; }
        public int Speed { get; set; }
        public int Duration { get; set; }
        public int DistanceOffset { get; set; }

        private float _calculatedSpeed;
        private Vector3 _endPosition;
        private int _movementPacketsSent;
        public enum LeapDirection
        {
            Both = 0,
            ForwardOnly = 1,
            BackwardOnly = 2
        }
        public LeapDirection Direction { get; set; }


        public LeapSkillController(SkillControllerTemplate template, Unit owner, BaseUnit target)
        {
            Template = template;
            Owner = owner;
            Target = target;

            Angle = template.Value[0];
            Speed = template.Value[1];
            Duration = template.Value[2];
            DistanceOffset = template.Value[3];
            Direction = (LeapDirection)template.Value[6];

            _endPosition = CalculateEndPosition(
                owner.Transform.World.Position,
                target.Transform.World.Position,
                owner.Transform.World.Rotation.Z,
                DistanceOffset);

            var distance = MathUtil.CalculateDistance(Owner.Transform.World.Position, _endPosition, true);
            var durationSeconds = Duration > 0 ? Duration / 1000f : 0.1f;
            _calculatedSpeed = distance / durationSeconds;

        }

        /// <summary>
        /// Resolves the AA 8 Leap destination. Self-target controllers advance
        /// along the owner's facing. Targeted controllers apply their offset from
        /// the target on the owner-to-target line. Offsets are stored in millimetres.
        /// </summary>
        public static Vector3 CalculateEndPosition(Vector3 ownerPosition, Vector3 targetPosition,
            float ownerFacingRadians, int distanceOffset)
        {
            var distanceMeters = distanceOffset / 1000f;
            if (ownerPosition == targetPosition)
            {
                return new Vector3(
                    ownerPosition.X - distanceMeters * MathF.Sin(ownerFacingRadians),
                    ownerPosition.Y + distanceMeters * MathF.Cos(ownerFacingRadians),
                    ownerPosition.Z);
            }

            var angleDegrees = MathUtil.CalculateAngleFrom(ownerPosition, targetPosition);
            var angleRadians = (float)(angleDegrees * Math.PI / 180d);
            var (endX, endY) = MathUtil.AddDistanceToFront(distanceMeters,
                targetPosition.X, targetPosition.Y, angleRadians);
            return new Vector3(endX, endY, targetPosition.Z);
        }

        public void Tick(TimeSpan delta)
        {
            if (IsForcedMovementBlocked(Owner))
            {
                if (ShouldTraceMovement())
                {
                    _log.Info(
                        "[AA8Movement] Leap blocked controller={0} owner={1} dead={2} actorNonPushable={3} buffNonPushable={4} knockbackImmune={5}",
                        Template.Id, Owner?.ObjId, Owner?.IsDead ?? true,
                        (Owner as Npc)?.Template?.NonPushableByActor ?? false,
                        Owner?.Buffs?.HasEffectsMatchingCondition(buff => buff.Template.NonPushable) ?? false,
                        Owner?.Buffs?.HasEffectsMatchingCondition(buff => buff.Template.KnockbackImmune) ?? false);
                }
                End();
                return;
            };
            MoveTowards(_calculatedSpeed * (float)(delta.TotalMilliseconds/1000f));
        }

        /// <summary>
        /// Leap controllers represent forced displacement. Stun/root/sleep stop
        /// voluntary movement but must not cancel the displacement that commonly
        /// accompanies those effects (Fending Arrow applies a 300 ms stun before
        /// controller 11359). Only the native push-immunity descriptors block it.
        /// </summary>
        public static bool ShouldBlockForcedMovement(bool isDead, bool actorNonPushable,
            bool buffNonPushable, bool knockbackImmune)
        {
            return isDead || actorNonPushable || buffNonPushable || knockbackImmune;
        }

        private static bool IsForcedMovementBlocked(Unit owner)
        {
            if (owner == null)
                return true;

            var actorNonPushable = (owner as Npc)?.Template?.NonPushableByActor ?? false;
            var buffNonPushable = owner.Buffs.HasEffectsMatchingCondition(buff =>
                buff.Template.NonPushable);
            var knockbackImmune = owner.Buffs.HasEffectsMatchingCondition(buff =>
                buff.Template.KnockbackImmune);
            return ShouldBlockForcedMovement(owner.IsDead, actorNonPushable,
                buffNonPushable, knockbackImmune);
        }

        private bool ShouldTraceMovement()
        {
            return Template.Id == 10258 || Template.Id == 11359 || Template.Id == 11360;
        }

        /// <summary>
        /// Controller 10258 has live-accepted AA8 phase metadata. Fending Arrow
        /// controllers are already represented by their plot event on the client;
        /// tagging every reconciliation movement as a new skill-controller phase
        /// leaves stale client state and crashes when the displaced NPC dies.
        /// </summary>
        public static (byte Flags, uint ScType) ResolveMovementWireContract(uint controllerId)
        {
            return controllerId == 10258
                ? ((byte)0x14, controllerId)
                : ((byte)0x04, 0u);
        }

        public override void Execute()
        {
            base.Execute();
            if (ShouldTraceMovement())
            {
                _log.Info(
                    "[AA8Movement] Leap execute controller={0} owner={1} target={2} from=<{3:F3},{4:F3},{5:F3}> to=<{6:F3},{7:F3},{8:F3}> speed={9:F3} duration={10}",
                    Template.Id, Owner?.ObjId, Target?.ObjId,
                    Owner.Transform.World.Position.X, Owner.Transform.World.Position.Y, Owner.Transform.World.Position.Z,
                    _endPosition.X, _endPosition.Y, _endPosition.Z, _calculatedSpeed, Duration);
            }
            TickManager.Instance.OnTick.Subscribe(Tick, TimeSpan.FromMilliseconds(100));
        }

        public override void End()
        {
            if (ShouldTraceMovement())
            {
                _log.Info(
                    "[AA8Movement] Leap end controller={0} owner={1} packets={2} state={3}",
                    Template.Id, Owner?.ObjId, _movementPacketsSent, State);
            }
            base.End();
            TickManager.Instance.OnTick.UnSubscribe(Tick);
        }

        public void MoveTowards(float distance, byte flags = 4)
        {
            var targetDist = MathUtil.CalculateDistance(Owner.Transform.World.Position, _endPosition);
            if (targetDist <= 1.0f)
            {
                //TODO End Skill Controller
                End();
                return;
            }

            var oldPosition = Owner.Transform.World.ClonePosition();

            var moveType = (UnitMoveType)MoveType.GetType(MoveTypeEnum.Unit);

            var travelDist = Math.Min(targetDist, distance);
            var angleDegrees = (float)MathUtil.CalculateAngleFrom(Owner.Transform.World.Position, _endPosition);
            var angleRadians = angleDegrees * MathF.PI / 180f;
            //var rotZ = MathUtil.ConvertDegreeToSByteDirection(angle);
            var (newX, newY) = MathUtil.AddDistanceToFront(travelDist, Owner.Transform.World.Position.X, Owner.Transform.World.Position.Y, angleRadians);
            var (velX, velY) = MathUtil.AddDistanceToFront(4000, 0, 0, angleRadians);
            var newZ = AppConfiguration.Instance.HeightMapsEnable ?
                WorldManager.Instance.GetHeight(Owner.Transform.ZoneId, newX, newY) :
                Owner.Transform.World.Position.Z;

            // TODO: Implement Transform.World
            Owner.Transform.World.SetPosition(newX,newY, newZ);
            Owner.Transform.World.SetRotationDegree(0f, 0f, angleDegrees - 90);



            moveType.X = Owner.Transform.Local.Position.X;
            moveType.Y = Owner.Transform.Local.Position.Y;
            moveType.Z = Owner.Transform.Local.Position.Z;
            moveType.VelX = (short)velX;
            moveType.VelY = (short)velY;
            var rpy = Owner.Transform.Local.ToRollPitchYawSBytesMovement();
            moveType.RotationX = 0; //rpy.Item1;
            moveType.RotationY = 0; //rpy.Item2;
            moveType.RotationZ = rpy.Item3;
            moveType.ActorFlags = ActorMoveType.Run; // 5-walk, 4-run, 3-stand still
            var wireContract = ResolveMovementWireContract(Template.Id);
            moveType.Flags = wireContract.Flags;
            moveType.ScType = wireContract.ScType;

            moveType.DeltaMovement = new sbyte[3];
            moveType.DeltaMovement[0] = 0;
            moveType.DeltaMovement[1] = 127;
            moveType.DeltaMovement[2] = 0;
            moveType.Stance = EStance.Combat;        // COMBAT = 0x0, IDLE = 0x1
            moveType.Alertness = AiAlertness.Combat; // IDLE = 0x0, ALERT = 0x1, COMBAT = 0x2
            moveType.Time = (uint)(DateTime.UtcNow - DateTime.UtcNow.Date).TotalMilliseconds;

            Owner.CheckMovedPosition(oldPosition);
            Owner.Transform.FinalizeTransform(true);
            Owner.BroadcastPacket(new SCOneUnitMovementPacket(Owner.ObjId, moveType), Owner is Character);
            _movementPacketsSent++;
            if (ShouldTraceMovement())
            {
                _log.Info(
                    "[AA8Movement] Leap movement controller={0} packet={1} owner={2} pos=<{3:F3},{4:F3},{5:F3}> remaining={6:F3} scType={7} flags=0x{8:X2}",
                    Template.Id, _movementPacketsSent, Owner.ObjId, newX, newY, newZ,
                    MathUtil.CalculateDistance(Owner.Transform.World.Position, _endPosition), moveType.ScType,
                    moveType.Flags);
            }

        }
    }
}
