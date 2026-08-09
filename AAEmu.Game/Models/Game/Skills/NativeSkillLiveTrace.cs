using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills
{
    /// <summary>
    /// Dispatches the shared skill lifecycle trace to specialization-specific
    /// allow-lists and records authoritative HP mutations for live acceptance.
    /// </summary>
    public static class NativeSkillLiveTrace
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

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
            SorceryLiveTrace.Record(
                phase,
                skill,
                caster,
                target,
                targetCount,
                effectCount,
                result,
                cancelled);
            ArcheryLiveTrace.Record(
                phase,
                skill,
                caster,
                target,
                targetCount,
                effectCount,
                result,
                cancelled);
        }

        public static void RecordDamage(
            Skill skill,
            Unit caster,
            Unit target,
            uint effectId,
            string damageType,
            int amount,
            int absorbed,
            int hpBefore,
            int hpAfter,
            bool packetBroadcast)
        {
            if (skill == null || caster == null || target == null)
                return;

            string tree;
            if (SorceryLiveTrace.IsTrackedSkill(skill.Id))
                tree = "sorcery";
            else if (ArcheryLiveTrace.IsTrackedSkill(skill.Id))
                tree = "archery";
            else
                return;

            Log.Info(FormatDamageEvent(
                tree,
                skill.Id,
                skill.TlId,
                effectId,
                caster.ObjId,
                target.ObjId,
                damageType,
                amount,
                absorbed,
                hpBefore,
                hpAfter,
                packetBroadcast));
        }

        public static void RecordCastingRelease(
            Skill skill,
            Unit caster,
            int castingPercent)
        {
            if (skill == null || caster == null)
                return;

            var tree = SorceryLiveTrace.IsTrackedSkill(skill.Id)
                ? "sorcery"
                : ArcheryLiveTrace.IsTrackedSkill(skill.Id) ? "archery" : null;
            if (tree == null)
                return;

            Log.Info(
                "[AA8SkillCastRelease] tree={0} skill={1} tlId={2} caster={3} percent={4}",
                tree,
                skill.Id,
                skill.TlId,
                caster.ObjId,
                castingPercent);
        }

        public static Skill ResolveOriginSkill(Skill directSkill, CastAction castAction)
        {
            if (directSkill != null)
                return directSkill;

            return (castAction as CastBuff)?.Buff?.Skill;
        }

        public static string FormatDamageEvent(
            string tree,
            uint skillId,
            ushort tlId,
            uint effectId,
            uint casterObjId,
            uint targetObjId,
            string damageType,
            int amount,
            int absorbed,
            int hpBefore,
            int hpAfter,
            bool packetBroadcast)
        {
            return string.Format(
                "[AA8SkillDamage] tree={0} skill={1} tlId={2} effect={3} caster={4} target={5} type={6} amount={7} absorbed={8} hpBefore={9} hpAfter={10} packet={11}",
                tree ?? "unknown",
                skillId,
                tlId,
                effectId,
                casterObjId,
                targetObjId,
                damageType ?? "unknown",
                amount,
                absorbed,
                hpBefore,
                hpAfter,
                packetBroadcast);
        }
    }
}
