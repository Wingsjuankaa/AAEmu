using System;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class MoveToGround : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.MoveToGround;

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
            if (caster is not Character character || target?.Transform == null)
                return;

            // Kakao 8.0 uses this server-authoritative effect for position-targeted
            // movement (Swiftblade Blink 40333, plot event 37838). The client-side
            // plot handler intentionally has no local implementation for type 73.
            var destination = target.Transform.World.Position;
            var previousPosition = character.Transform.World.ClonePosition();

            _log.Debug(
                "[AA8Movement] MoveToGround skill={0} caster={1} targetType={2} destination=<{3:F3},{4:F3},{5:F3}>",
                skill?.Template?.Id ?? 0,
                character.ObjId,
                target.ObjId == uint.MaxValue ? "position" : "unit",
                destination.X,
                destination.Y,
                destination.Z);

            character.Transform.Local.SetPosition(destination.X, destination.Y, destination.Z);
            character.CheckMovedPosition(previousPosition);
            character.Transform.FinalizeTransform(true);
            character.BroadcastPacket(new SCUnitBlinkPacket(
                character.ObjId, 0f, 0f, false,
                destination.X, destination.Y, destination.Z), true);
        }
    }
}
