using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class TeleportToUnit : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.TeleportToUnit;
        
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
            _log.Trace("value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4);
            if (target == null)
            {
                //this shouldn't happen?
                return;
            }

            var pos = target.Transform.World.Position;
            var distance = (float)value1 / 1000f;
            var (endX, endY) = MathUtil.AddDistanceToFront(distance, target.Transform.World.Position.X, target.Transform.World.Position.Y, target.Transform.World.ToRollPitchYawDegrees().Z);
            
            switch (caster)
            {
                case Character character:
                    var oldPosition = character.Transform.World.ClonePosition();
                    var z = AppConfiguration.Instance.HeightMapsEnable
                        ? WorldManager.Instance.GetHeight(character.Transform.ZoneId, endX, endY)
                        : pos.Z;
                    character.Transform.Local.SetPosition(endX, endY, z);
                    character.CheckMovedPosition(oldPosition);
                    character.Transform.FinalizeTransform(true);
                    character.BroadcastPacket(new SCUnitBlinkPacket(caster.ObjId, 0f, 0f, false,
                        endX, endY, z), true);
                    break;
                case Npc npc:
                    npc.MoveTowards(pos, 10000);
                    npc.StopMovement();
                    break;
            }
        }
    }
}
