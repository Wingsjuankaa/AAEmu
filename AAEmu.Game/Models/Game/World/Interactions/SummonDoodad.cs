using System.Numerics;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.World.Interactions
{
    public class SummonDoodad : IWorldInteraction
    {
        public void Execute(Unit caster, SkillCaster casterType, BaseUnit target, SkillCastTarget targetType,
            uint skillId, uint doodadId, DoodadFuncTemplate objectFunc)
        {
            ExecuteWithSourceDirection(caster, casterType, target, targetType,
                skillId, doodadId, false);
        }

        public void ExecuteWithSourceDirection(Unit caster, SkillCaster casterType, BaseUnit target,
            SkillCastTarget targetType, uint skillId, uint doodadId, bool sourceDirection,
            Skill originSkill = null)
        {
            var doodad = DoodadManager.Instance.Create(0, doodadId, caster);
            if (doodad == null)
                return;

            doodad.OriginSkill = originSkill;
            doodad.Transform = target.Transform.CloneDetached(doodad);
            var rotation = ResolveSummonedRotation(
                doodad.Transform.Local.Rotation,
                caster.Transform.World.Rotation,
                sourceDirection);
            doodad.Transform.Local.SetRotation(rotation.X, rotation.Y, rotation.Z);
            doodad.Spawn();
        }

        public static Vector3 ResolveSummonedRotation(
            Vector3 targetRotation, Vector3 sourceRotation, bool sourceDirection)
        {
            return sourceDirection ? sourceRotation : targetRotation;
        }
    }
}
