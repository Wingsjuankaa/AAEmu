using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Tasks.Doodads;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs
{
    public class DoodadFuncClout : DoodadPhaseFuncTemplate
    {
        // doodad_phase_funcs
        public int Duration { get; set; }
        public int Tick { get; set; }
        public SkillTargetRelation TargetRelation { get; set; }
        public uint BuffId { get; set; }
        public uint ProjectileId { get; set; }
        public bool ShowToFriendlyOnly { get; set; }
        public int NextPhase { get; set; }
        public uint AoeShapeId { get; set; }
        public uint TargetBuffTagId { get; set; }
        public uint TargetNoBuffTagId { get; set; }
        public bool UseOriginSource { get; set; }
        public List<uint> Effects { get; set; }

        public override int GetPhaseDuration(Doodad owner) => Duration;

        public override bool Use(Unit caster, Doodad owner)
        {
            _log.Trace("DoodadFuncClout : Duration {0}, Tick {1}, TargetRelationId {2}, BuffId {3}," +
                       " ProjectileId {4}, ShowToFriendlyOnly {5}, NextPhase {6}, AoeShapeId {7}," +
                       " TargetBuffTagId {8}, TargetNoBuffTagId {9}, UseOriginSource {10}",
                Duration, Tick, TargetRelation, BuffId, ProjectileId, ShowToFriendlyOnly, NextPhase, AoeShapeId, TargetBuffTagId, TargetNoBuffTagId, UseOriginSource);

            var originSkill = AreaTrigger.SelectOriginSkill(UseOriginSource, owner.OriginSkill);
            var areaTrigger = new AreaTrigger()
            {
                Shape = WorldManager.Instance.GetAreaShapeById(AoeShapeId),
                Owner = owner,
                Caster = caster,
                InsideBuffTemplate = SkillManager.Instance.GetBuffTemplate(BuffId),
                TargetRelation = TargetRelation,
                TargetBuffTagId = TargetBuffTagId,
                TargetNoBuffTagId = TargetNoBuffTagId,
                TickRate = Tick,
                EffectPerTick = Effects.Select(eid => SkillManager.Instance.GetEffectTemplate(eid)).ToList(),
                OriginSkill = originSkill,
                SkillId = originSkill?.Id ?? 0,
                TlId = originSkill?.TlId ?? 0
            };

            AreaTriggerManager.Instance.AddAreaTrigger(areaTrigger);

            if (Duration > 0)
            {
                owner.GrowthTime = System.DateTime.UtcNow.AddMilliseconds(Duration);
                // Doodad and area-trigger state belongs to the game scheduler. Running
                // this lifecycle through Task.Run can race region visibility updates:
                // the client receives SCDoodadRemoved while the continuous phase
                // prefab is still reachable and can be sent again on a region change.
                owner.FuncTask = new DoodadFuncCloutTask(caster, owner, NextPhase, areaTrigger);
                TaskManager.Instance.Schedule(
                    owner.FuncTask,
                    System.TimeSpan.FromMilliseconds(Duration));
            }

            return false;
        }
    }
}
