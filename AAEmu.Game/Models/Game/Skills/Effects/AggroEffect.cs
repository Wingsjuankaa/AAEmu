using System;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class AggroEffect : EffectTemplate
    {
        public bool UseFixedAggro { get; set; }
        public int FixedMin { get; set; }
        public int FixedMax { get; set; }
        public bool UseLevelAggro { get; set; }
        public float LevelMd { get; set; }
        public int LevelVaStart { get; set; }
        public int LevelVaEnd { get; set; }
        public bool UseChargedBuff { get; set; }
        public uint ChargedBuffId { get; set; }
        public float ChargedMul { get; set; }

        public override bool OnActionTime => false;
        
        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj,
            EffectSource source, SkillObject skillObject, DateTime time, CompressedGamePackets packetBuilder = null)
        {
            if (!(caster is Character character))
                return;
            
            if (!(target is Npc npc))
                return;

            var template = source.Skill?.Template;
            var abilityLevel = template != null
                ? caster.GetAbLevel((AbilityType)template.AbilityId)
                : 1;
            var range = AggroEffectCalculator.CalculateBaseAggroRange(
                UseFixedAggro,
                FixedMin,
                FixedMax,
                UseLevelAggro,
                caster.LevelDps,
                abilityLevel,
                template?.AbilityLevel ?? 1,
                template?.CastingInc ?? 0,
                LevelMd,
                LevelVaStart,
                LevelVaEnd);
            var min = (float)range.Min;
            var max = (float)range.Max;

            if (UseChargedBuff)
            {
                var effect = caster.Buffs.GetEffectFromBuffId(ChargedBuffId);
                if (effect != null)
                {
                    min += ChargedMul * effect.Charge;
                    max += ChargedMul * effect.Charge;
                    effect.Exit();
                }
            }

            var value = max <= min
                ? (int)min
                : (int)Rand.Next(min, max);
            npc.AddUnitAggro(AggroKind.Damage, character, value);
        }
    }
}
