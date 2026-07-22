using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;

using NLog;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class Blink : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.Blink;
        
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

            if (caster is Character character)
            {
                var oldPosition = character.Transform.World.ClonePosition();
                var newPos = character.Transform.CloneDetached();
                newPos.Local.AddDistanceToFront(value1);
                var z = AppConfiguration.Instance.HeightMapsEnable
                    ? WorldManager.Instance.GetHeight(character.Transform.ZoneId, newPos.Local.Position.X, newPos.Local.Position.Y)
                    : newPos.Local.Position.Z;

                character.Transform.Local.SetPosition(newPos.Local.Position.X, newPos.Local.Position.Y, z);
                character.CheckMovedPosition(oldPosition);
                character.Transform.FinalizeTransform(true);
                character.BroadcastPacket(new SCUnitBlinkPacket(caster.ObjId, value1, value2, false,
                    newPos.Local.Position.X, newPos.Local.Position.Y, z), true);
            }
        }
    }
}
