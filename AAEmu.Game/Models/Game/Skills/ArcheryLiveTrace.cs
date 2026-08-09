using System.Collections.Generic;
using System.Globalization;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Skills
{
    /// <summary>
    /// Structured, behavior-neutral evidence for the AA8 Archery live gate.
    /// The allow-list is the complete executable Archery V1 skill closure.
    /// </summary>
    public static class ArcheryLiveTrace
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

        private static readonly HashSet<uint> TrackedSkillIds = new HashSet<uint>
        {
            10694, 10708, 11368, 11933, 12133, 12759, 12792, 12793,
            12794, 13281, 14835, 14836, 14837, 15073, 15096, 16210,
            23592, 36468, 36469, 36470, 36471, 36472, 36473, 38893,
            39663, 39664, 39665, 39666, 39667, 39668, 40580, 41219,
            41221, 42849, 42851
        };

        private static readonly HashSet<uint> TrackedPassiveIds = new HashSet<uint>
        {
            2, 7, 35, 255, 256, 300
        };

        public static int TrackedSkillCount => TrackedSkillIds.Count;

        public static int TrackedPassiveCount => TrackedPassiveIds.Count;

        public static bool IsTrackedSkill(uint skillId)
        {
            return TrackedSkillIds.Contains(skillId);
        }

        public static bool IsTrackedPassive(uint passiveId)
        {
            return TrackedPassiveIds.Contains(passiveId);
        }

        public static void RecordPassiveSnapshot(
            string phase,
            Character character,
            uint passiveId,
            uint buffId)
        {
            if (character == null || !IsTrackedPassive(passiveId))
                return;

            var endless = BuildProbeSkill(14835);
            var concussive = BuildProbeSkill(11933);
            var endlessDamage = endless == null
                ? -1d
                : character.ApplySkillModifiers(endless, SkillAttribute.Damage, 100d);
            var endlessRange = endless == null
                ? -1d
                : character.ApplySkillModifiers(
                    endless,
                    SkillAttribute.Range,
                    endless.Template.MaxRange);
            var concussiveCooldown = concussive == null
                ? -1d
                : character.ApplySkillModifiers(
                    concussive,
                    SkillAttribute.Cooldown,
                    concussive.Template.CooldownTime);

            Log.Info(FormatPassiveSnapshot(
                phase,
                passiveId,
                buffId,
                character.ObjId,
                character.MoveSpeedMul,
                character.RangedAccuracy,
                character.RangedCritical,
                character.RangedCriticalBonus,
                character.RangedCriticalMul,
                character.RangedDamageMul,
                endlessDamage,
                endlessRange,
                concussiveCooldown));
        }

        private static Skill BuildProbeSkill(uint skillId)
        {
            var template = SkillManager.Instance.GetSkillTemplate(skillId);
            return template == null
                ? null
                : new Skill { Id = skillId, Template = template, Level = 1 };
        }

        public static string FormatPassiveSnapshot(
            string phase,
            uint passiveId,
            uint buffId,
            uint characterObjId,
            double moveSpeedMultiplier,
            double rangedAccuracy,
            double rangedCritical,
            double rangedCriticalBonus,
            double rangedCriticalMultiplier,
            double rangedDamageMultiplier,
            double endlessDamagePercent,
            double endlessRange,
            double concussiveCooldown)
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "[AA8ArcheryPassive] phase={0} passive={1} buff={2} char={3} move={4:F4} rangedAccuracy={5:F4} rangedCritical={6:F4} rangedCriticalBonus={7:F4} rangedCriticalMul={8:F4} rangedDamageMul={9:F4} endlessDamage={10:F4} endlessRange={11:F4} concussiveCooldown={12:F4}",
                phase ?? "unknown",
                passiveId,
                buffId,
                characterObjId,
                moveSpeedMultiplier,
                rangedAccuracy,
                rangedCritical,
                rangedCriticalBonus,
                rangedCriticalMultiplier,
                rangedDamageMultiplier,
                endlessDamagePercent,
                endlessRange,
                concussiveCooldown);
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
            int targetCount,
            int effectCount,
            SkillResult? result,
            bool? cancelled)
        {
            return string.Format(
                "[AA8ArcheryLive] phase={0} skill={1} tlId={2} caster={3} target={4} world={5} instance={6} mp={7} targets={8} effects={9} result={10} cancelled={11}",
                phase ?? "unknown",
                skillId,
                tlId,
                casterObjId,
                targetObjId,
                worldId,
                instanceId,
                mp,
                targetCount,
                effectCount,
                result?.ToString() ?? "-",
                cancelled?.ToString() ?? "-");
        }
    }
}
