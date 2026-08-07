using System;

using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    public class SpawnDoodad : SpecialEffectAction
    {
        protected override SpecialType SpecialEffectActionType => SpecialType.SpawnDoodad;
        
        public override void Execute(Unit caster,
            SkillCaster casterObj,
            BaseUnit target,
            SkillCastTarget targetObj,
            CastAction castObj,
            Skill skill,
            SkillObject skillObject,
            DateTime time,
            int doodadId,
            int value2, // sometimes 1000
            int value3,
            int value4)
        {
            if (doodadId <= 0 || caster == null)
                return;

            var anchor = target?.Transform != null ? target : caster;
            var doodad = DoodadManager.Instance.Create(0, (uint)doodadId, caster);
            if (doodad == null)
            {
                _log.Warn("SpawnDoodad references missing doodad template {0}", doodadId);
                return;
            }

            // AA8 plot effects address spawned doodads through target_id=Location.
            // The synthetic target already contains the position, rotation, world
            // and instance selected by the plot target-update method.
            doodad.Transform = anchor.Transform.CloneDetached(doodad);
            doodad.Spawn();
        }
    }
}
