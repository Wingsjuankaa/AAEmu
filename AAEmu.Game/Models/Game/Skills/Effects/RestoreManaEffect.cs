using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class RestoreManaEffect : EffectTemplate
    {
        public bool UseFixedValue { get; set; }
        public int FixedMin { get; set; }
        public int FixedMax { get; set; }
        public bool UseLevelValue { get; set; }
        public float LevelMd { get; set; }
        public int LevelVaStart { get; set; }
        public int LevelVaEnd { get; set; }
        public bool Percent { get; set; }

        public override bool OnActionTime => false;

        public static float CalculateLevelScale(int casterLevel, int abilityLevel, int levelStep)
        {
            return Math.Max(0f, (casterLevel - abilityLevel) * levelStep / 1000f);
        }

        public static (float Min, float Max) CalculateRestoreRange(
            float levelDps,
            int casterLevel,
            int abilityLevel,
            int levelStep,
            bool useFixedValue,
            int fixedMin,
            int fixedMax,
            bool useLevelValue,
            float levelMd,
            int levelVaStart,
            int levelVaEnd,
            bool percent,
            int maxMp,
            double tickModifier = 1d)
        {
            var min = useFixedValue ? fixedMin : 0f;
            var max = useFixedValue ? fixedMax : 0f;

            if (useLevelValue)
            {
                var scale = CalculateLevelScale(casterLevel, abilityLevel, levelStep);
                var levelBase = levelDps * ((scale + 1f) * levelMd);
                var variation = (((casterLevel - 1f) / 49f) * (levelVaEnd - levelVaStart) + levelVaStart) * 0.01f;
                min += (int)(levelBase - variation * levelBase + 0.5f);
                max += (int)((variation + 1f) * levelBase + 0.5f);
            }

            // Native restore-mana percentage values use the common AA8 per-mille scale.
            if (percent)
            {
                min = min * maxMp / 1000f;
                max = max * maxMp / 1000f;
            }

            var boundedTickModifier = Math.Max(0d, tickModifier);
            min = (float)(min * boundedTickModifier);
            max = (float)(max * boundedTickModifier);
            return min <= max ? (min, max) : (max, min);
        }

        public static int ClampMana(int currentMp, int delta, int maxMp)
        {
            var result = (long)currentMp + delta;
            return (int)Math.Max(0L, Math.Min(Math.Max(0, maxMp), result));
        }

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj,
            EffectSource source, SkillObject skillObject, DateTime time, CompressedGamePackets packetBuilder = null)
        {
            _log.Trace("RestoreManaEffect");

            if (!(target is Unit trg))
                return;

            var skillTemplate = source?.Skill?.Template;
            var tickModifier = source?.Buff != null && source.Buff.TickEffects.Count > 0 && source.Buff.Duration > 0
                ? source.Buff.Tick / source.Buff.Duration
                : 1d;
            var range = CalculateRestoreRange(
                caster.LevelDps,
                caster.Level,
                skillTemplate?.AbilityLevel ?? caster.Level,
                skillTemplate?.LevelStep ?? 0,
                UseFixedValue,
                FixedMin,
                FixedMax,
                UseLevelValue,
                LevelMd,
                LevelVaStart,
                LevelVaEnd,
                Percent,
                trg.MaxMp,
                tickModifier);
            var value = range.Min == range.Max ? (int)range.Min : (int)Rand.Next(range.Min, range.Max);

            var packet = new SCUnitHealedPacket(castObj, casterObj, trg.ObjId, 1, 13, value);
            if (packetBuilder != null)
                packetBuilder.AddPacket(packet);
            else
                trg.BroadcastPacket(packet, true);

            trg.Mp = ClampMana(trg.Mp, value, trg.MaxMp);
            trg.BroadcastPacket(new SCUnitPointsPacket(trg.ObjId, trg.Hp, trg.Mp), true);
        }
    }
}
