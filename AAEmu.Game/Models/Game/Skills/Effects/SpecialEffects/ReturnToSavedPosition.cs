using System;
using System.Numerics;

using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    /// <summary>
    /// Returns a character to the position captured by the save_pos buff whose
    /// native id is carried in value1. The AA8 descriptor removes that buff in
    /// a separate DispelEffect, so this action only performs the movement.
    /// </summary>
    public class ReturnToSavedPosition : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.ReturnToSavedPosition;

        public static bool TryResolveDestination(
            Character character,
            Buff positionBuff,
            out Vector3 destination)
        {
            destination = default;
            if (character == null || positionBuff?.SavedPosition == null)
                return false;
            if (positionBuff.SavedWorldId != character.Transform.WorldId ||
                positionBuff.SavedInstanceId != character.Transform.InstanceId)
                return false;

            destination = positionBuff.SavedPosition.Value;
            return true;
        }

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
            var character = target as Character ?? caster as Character;
            if (character == null || value1 <= 0)
                return;

            var positionBuff = character.Buffs.GetEffectFromBuffId((uint)value1);
            if (positionBuff?.SavedPosition == null)
            {
                _log.Warn(
                    "[AA8Movement] ReturnToSavedPosition missing saved buff caster={0} buff={1}",
                    character.ObjId,
                    value1);
                return;
            }

            if (!TryResolveDestination(character, positionBuff, out var destination))
            {
                _log.Warn(
                    "[AA8Movement] ReturnToSavedPosition rejected cross-world return caster={0} buff={1}",
                    character.ObjId,
                    value1);
                return;
            }

            var previousPosition = character.Transform.World.ClonePosition();
            character.Transform.Local.SetPosition(destination.X, destination.Y, destination.Z);
            character.CheckMovedPosition(previousPosition);
            character.Transform.FinalizeTransform(true);
            character.BroadcastPacket(new SCUnitBlinkPacket(
                character.ObjId, 0f, 0f, false,
                destination.X, destination.Y, destination.Z), true);

            _log.Debug(
                "[AA8Movement] ReturnToSavedPosition skill={0} caster={1} buff={2} destination=<{3:F3},{4:F3},{5:F3}>",
                skill?.Template?.Id ?? 0,
                character.ObjId,
                value1,
                destination.X,
                destination.Y,
                destination.Z);
        }
    }
}
