using System;
using System.Numerics;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Movements;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class KnockBack : SpecialEffectAction
    {
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int value1,
            int value2,
            int value3,
            int value4)
        {
            if (!(target is Npc npc) || caster == null || value1 <= 0)
                return;

            // The AA8 client applies native actor physics for characters. Moving
            // them here as well produces a double displacement. NPC positions,
            // on the other hand, need a server reconciliation proxy.
            if ((npc.Template?.NonPushableByActor ?? false) ||
                npc.Buffs.HasEffectsMatchingCondition(buff => buff.Template.NonPushable))
                return;

            var displacement = ForcedMovementEffectCalculator.CalculateKnockBackDisplacement(
                caster.Transform.World.Position,
                npc.Transform.World.Position,
                value1,
                value2);
            ApplyForcedMovementToNpc(npc, displacement, TimeSpan.FromMilliseconds(600));

            _log.Trace(
                "AA8 KnockBack npc={0} magnitudeMm={1} elevationDeg={2} displacement=<{3:F3},{4:F3},{5:F3}>",
                npc.ObjId, value1, value2, displacement.X, displacement.Y, displacement.Z);
        }

        internal static void ApplyForcedMovementToNpc(Npc npc, Vector3 displacement, TimeSpan movementGuard)
        {
            if (npc == null || displacement.LengthSquared() < 0.000001f)
                return;

            var oldPosition = npc.Transform.World.ClonePosition();
            var current = npc.Transform.World.Position;
            var newX = current.X + displacement.X;
            var newY = current.Y + displacement.Y;
            var terrainHeight = WorldManager.Instance.GetHeight(npc.Transform.ZoneId, newX, newY);
            var newZ = Math.Max(current.Z + displacement.Z, terrainHeight);

            npc.Transform.Local.SetPosition(newX, newY, newZ);
            npc.Transform.FinalizeTransform(true);
            npc.DisplacedUntil = DateTime.UtcNow.Add(movementGuard);

            var moveType = (UnitMoveType)MoveType.GetType(MoveTypeEnum.Unit);
            moveType.X = npc.Transform.Local.Position.X;
            moveType.Y = npc.Transform.Local.Position.Y;
            moveType.Z = npc.Transform.Local.Position.Z;
            var (rotationX, rotationY, rotationZ) = npc.Transform.Local.ToRollPitchYawSBytesMovement();
            moveType.RotationX = rotationX;
            moveType.RotationY = rotationY;
            moveType.RotationZ = rotationZ;
            moveType.ActorFlags = ActorMoveType.StandStill;
            moveType.Flags = 0;
            moveType.DeltaMovement = new sbyte[3];
            moveType.Stance = EStance.Combat;
            moveType.Alertness = AiAlertness.Combat;
            moveType.Time = (uint)(DateTime.UtcNow - DateTime.UtcNow.Date).TotalMilliseconds;

            npc.CheckMovedPosition(oldPosition);
            npc.BroadcastPacket(new SCOneUnitMovementPacket(npc.ObjId, moveType), false);
        }
    }
}
