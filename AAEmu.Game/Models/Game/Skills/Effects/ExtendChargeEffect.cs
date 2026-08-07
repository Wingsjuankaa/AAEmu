using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// Backend for the charged buff used by AA8 absorption shields.
    /// </summary>
    /// <remarks>
    /// The fixed/level/DPS arithmetic uses the same native damage primitive that
    /// drives the client tooltip's avg_damage placeholder. AA10's stable row adds
    /// the resource selector that AA8's compact cache did not expose; for
    /// Insulating Lens it is independently corroborated by the AA8 description
    /// (5% maximum mana).
    /// </remarks>
    public class ExtendChargeEffect : EffectTemplate
    {
        public uint ChargeBuffId { get; set; }
        public int DamageTypeId { get; set; }
        public float DpsIncMultiplier { get; set; }
        public float DpsMultiplier { get; set; }
        public int FixedMax { get; set; }
        public int FixedMin { get; set; }
        public float LevelMd { get; set; }
        public int LevelVaEnd { get; set; }
        public int LevelVaStart { get; set; }
        public int PercentMax { get; set; }
        public int PercentMin { get; set; }
        public bool UseCurrentHealth { get; set; }
        public int PercentDamageResourceTypeId { get; set; }
        public bool UseSourceHealth { get; set; }
        public bool UseDpsCharge { get; set; }
        public bool UseFixedCharge { get; set; }
        public bool UseLevelCharge { get; set; }
        public bool UseMainhandWeapon { get; set; }
        public bool UseOffhandWeapon { get; set; }
        public bool UsePercentCharge { get; set; }
        public bool UseRangedWeapon { get; set; }

        public override bool OnActionTime => false;

        public static (float Min, float Max) CalculateChargeRange(
            float levelDps,
            int abilityLevel,
            int requiredAbilityLevel,
            int castingInc,
            int castingTime,
            float dpsInc,
            float mainhandDps,
            float offhandDps,
            float rangedDps,
            int currentHealth,
            int maxHealth,
            int currentMana,
            int maxMana,
            bool useFixedCharge,
            int fixedMin,
            int fixedMax,
            bool useLevelCharge,
            float levelMd,
            int levelVaStart,
            int levelVaEnd,
            bool useDpsCharge,
            float dpsIncMultiplier,
            float dpsMultiplier,
            bool useMainhandWeapon,
            bool useOffhandWeapon,
            bool useRangedWeapon,
            bool usePercentCharge,
            int percentMin,
            int percentMax,
            int percentDamageResourceTypeId)
        {
            var weaponDps = 0f;
            if (useDpsCharge && useMainhandWeapon)
                weaponDps += mainhandDps;
            if (useDpsCharge && useOffhandWeapon)
                weaponDps += offhandDps;
            if (useDpsCharge && useRangedWeapon)
                weaponDps += rangedDps;

            var baseRange = DamageEffectCalculator.CalculateBaseDamageRange(
                useFixedCharge,
                fixedMin,
                fixedMax,
                useLevelCharge,
                levelDps,
                abilityLevel,
                requiredAbilityLevel,
                castingInc,
                levelMd,
                levelVaStart,
                levelVaEnd,
                useDpsCharge ? (int)dpsInc : 0,
                dpsIncMultiplier,
                (int)weaponDps,
                dpsMultiplier,
                castingTime,
                0,
                1f,
                1f);
            var min = (float)baseRange.Min;
            var max = (float)baseRange.Max;

            if (usePercentCharge)
            {
                var resource = 0;
                switch (percentDamageResourceTypeId)
                {
                    case 1: // enum_percent_damage_resource_types.current_health
                        resource = currentHealth;
                        break;
                    case 2: // max_health
                        resource = maxHealth;
                        break;
                    case 3: // current_mana
                        resource = currentMana;
                        break;
                    case 4: // max_mana
                        resource = maxMana;
                        break;
                }
                min += Math.Max(0, resource) * percentMin / 100f;
                max += Math.Max(0, resource) * percentMax / 100f;
            }

            min = Math.Max(0f, min);
            max = Math.Max(0f, max);
            return min <= max ? (min, max) : (max, min);
        }

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source,
            SkillObject skillObject, DateTime time,
            CompressedGamePackets packetBuilder = null)
        {
            var trg = target as Unit;
            if (trg == null || ChargeBuffId == 0)
                return;

            var buffTemplate = SkillManager.Instance.GetBuffTemplate(ChargeBuffId);
            if (buffTemplate == null)
            {
                _log.Warn("ExtendChargeEffect {0} references missing buff {1}", Id, ChargeBuffId);
                return;
            }

            var skillTemplate = source?.Skill?.Template;
            var abilityLevel = skillTemplate != null
                ? caster.GetAbLevel((AbilityType)skillTemplate.AbilityId)
                : caster.Level;
            var dpsInc = 0f;
            switch ((DamageType)DamageTypeId)
            {
                case DamageType.Melee:
                    dpsInc = caster.DpsInc;
                    break;
                case DamageType.Magic:
                    dpsInc = caster.MDps + caster.MDpsInc;
                    break;
                case DamageType.Ranged:
                    dpsInc = caster.RangedDpsInc;
                    break;
            }

            var resourceOwner = UseSourceHealth ? caster : trg;
            var range = CalculateChargeRange(
                caster.LevelDps,
                abilityLevel,
                skillTemplate?.AbilityLevel ?? abilityLevel,
                skillTemplate?.CastingInc ?? 0,
                skillTemplate?.CastingTime ?? 0,
                dpsInc,
                caster.Dps,
                caster.OffhandDps,
                caster.RangedDps,
                resourceOwner.Hp,
                resourceOwner.MaxHp,
                resourceOwner.Mp,
                resourceOwner.MaxMp,
                UseFixedCharge,
                FixedMin,
                FixedMax,
                UseLevelCharge,
                LevelMd,
                LevelVaStart,
                LevelVaEnd,
                UseDpsCharge,
                DpsIncMultiplier,
                DpsMultiplier,
                UseMainhandWeapon,
                UseOffhandWeapon,
                UseRangedWeapon,
                UsePercentCharge,
                PercentMin,
                PercentMax,
                PercentDamageResourceTypeId != 0
                    ? PercentDamageResourceTypeId
                    : (UseCurrentHealth ? 1 : 4));
            var charge = range.Min == range.Max
                ? (int)range.Min
                : (int)Rand.Next(range.Min, range.Max);
            if (charge <= 0)
                return;

            trg.Buffs.AddBuff(new Buff(trg, caster, casterObj, buffTemplate, source?.Skill, time)
            {
                Charge = charge
            });
        }
    }
}
