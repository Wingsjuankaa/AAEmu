using System.Collections.Generic;

using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills
{
    /// <summary>
    /// Structured, behavior-neutral evidence for the AA8 Sorcery live gate.
    /// The allow-list is generated from the V3 executable closure: 30 entry
    /// points plus every reachable child skill, for 43 distinct skill IDs.
    /// </summary>
    public static class SorceryLiveTrace
    {
        private const uint MagicSourceResourceId = 8;

        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

        private static readonly HashSet<uint> TrackedSkillIds = new HashSet<uint>
        {
            10151, 10153, 10664, 10667, 10670, 10752, 11314, 11939,
            11967, 12789, 12790, 12791, 12796, 14774, 15317, 23593,
            23646, 23647, 23648, 23649, 24894, 24895, 36474, 36475,
            36476, 36477, 36478, 36479, 37837, 39669, 39670, 39671,
            39672, 39673, 39674, 41222, 41223, 41478, 42012, 43068,
            43185, 43464, 43465
        };

        public static int TrackedSkillCount => TrackedSkillIds.Count;

        public static bool IsTrackedSkill(uint skillId)
        {
            return TrackedSkillIds.Contains(skillId);
        }

        public static void Record(
            string phase,
            Skill skill,
            Unit caster,
            BaseUnit target = null,
            int targetCount = -1,
            int effectCount = -1,
            SkillResult? result = null,
            bool? cancelled = null)
        {
            if (skill == null || caster == null || !IsTrackedSkill(skill.Id))
                return;

            Log.Info(FormatEvent(
                phase,
                skill.Id,
                skill.TlId,
                caster.ObjId,
                target?.ObjId ?? 0,
                caster.Transform?.WorldId ?? 0,
                caster.Transform?.InstanceId ?? 0,
                caster.Mp,
                caster.GetCombatResource(MagicSourceResourceId),
                targetCount,
                effectCount,
                result,
                cancelled));
        }

        public static string FormatEvent(
            string phase,
            uint skillId,
            ushort tlId,
            uint casterObjId,
            uint targetObjId,
            uint worldId,
            uint instanceId,
            int mp,
            long magicSource,
            int targetCount,
            int effectCount,
            SkillResult? result,
            bool? cancelled)
        {
            return string.Format(
                "[AA8SorceryLive] phase={0} skill={1} tlId={2} caster={3} target={4} world={5} instance={6} mp={7} magicSource={8} targets={9} effects={10} result={11} cancelled={12}",
                phase ?? "unknown",
                skillId,
                tlId,
                casterObjId,
                targetObjId,
                worldId,
                instanceId,
                mp,
                magicSource,
                targetCount,
                effectCount,
                result?.ToString() ?? "-",
                cancelled?.ToString() ?? "-");
        }
    }
}
