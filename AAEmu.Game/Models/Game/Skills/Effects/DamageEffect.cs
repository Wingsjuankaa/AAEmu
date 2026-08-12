using System;
using System.Collections.Generic;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Procs;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Route;
using AAEmu.Game.Models.Mechanics;
using AAEmu.Game.Models.Tasks.UnitMove;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class DamageEffect : EffectTemplate
    {
        public DamageType DamageType { get; set; }
        public int FixedMin { get; set; }
        public int FixedMax { get; set; }
        public float Multiplier { get; set; }
        public bool UseMainhandWeapon { get; set; }
        public bool UseOffhandWeapon { get; set; }
        public bool UseRangedWeapon { get; set; }
        public int CriticalBonus { get; set; }
        public uint TargetBuffTagId { get; set; }
        public int TargetBuffBonus { get; set; }
        public bool UseFixedDamage { get; set; }
        public bool UseLevelDamage { get; set; }
        public float LevelMd { get; set; }
        public int LevelVaStart { get; set; }
        public int LevelVaEnd { get; set; }
        public float TargetBuffBonusMul { get; set; }
        public bool UseChargedBuff { get; set; }
        public uint ChargedBuffId { get; set; }
        public float ChargedMul { get; set; }
        public float AggroMultiplier { get; set; }
        public int HealthStealRatio { get; set; }
        public int ManaStealRatio { get; set; }
        public float DpsMultiplier { get; set; }
        public int WeaponSlotId { get; set; }
        public bool CheckCrime { get; set; }
        public uint HitAnimTimingId { get; set; }
        public bool UseTargetChargedBuff { get; set; }
        public uint TargetChargedBuffId { get; set; }
        public float TargetChargedMul { get; set; }
        public float DpsIncMultiplier { get; set; }
        public bool EngageCombat { get; set; }
        public bool Synergy { get; set; }
        public uint ActabilityGroupId { get; set; }
        public int ActabilityStep { get; set; }
        public float ActabilityMul { get; set; }
        public float ActabilityAdd { get; set; }
        public float ChargedLevelMul { get; set; }
        public bool AdjustDamageByHeight { get; set; }
        public bool UsePercentDamage { get; set; }
        public int PercentMin { get; set; }
        public int PercentMax { get; set; }
        public bool UseCurrentHealth { get; set; }
        public int TargetHealthMin { get; set; }
        public int TargetHealthMax { get; set; }
        public float TargetHealthMul { get; set; }
        public int TargetHealthAdd { get; set; }
        public bool FireProc { get; set; }
        public float HighAbilityResourceDpsMd { get; set; }
        public float HighAbilityResourceLevelMd { get; set; }
        public float HighAbilityResourceMd { get; set; }
        public bool UseHighAbilityResource { get; set; }
        public bool ManaDamage { get; set; }
        public bool AdjustDamageByRange { get; set; }
        public bool CancelProtection { get; set; }
        public bool Crime { get; set; }
        public int FixedType { get; set; }
        public float OptimumRange { get; set; }
        public float RangeDamageMultiplier { get; set; }
        public bool UseElementEffect { get; set; }
        public bool UseSourceHealth { get; set; }
        public List<BonusTemplate> Bonuses { get; set; } = new List<BonusTemplate>();

        public override bool OnActionTime => false;

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj, EffectSource source, SkillObject skillObject, DateTime time,
            CompressedGamePackets packetBuilder = null)
        {
            _log.Trace("DamageEffect");

            var trg = target as Unit;
            if (trg == null || trg.Hp <= 0)
            {
                TraceLab("damage_skipped", caster, target,
                    $"effect={Id} reason=invalid_or_dead hp={trg?.Hp ?? -1}");
                return;
            }

            if (Bonuses != null)
            {
                foreach(var bonus in Bonuses)
                {
                    caster.AddBonus(uint.MaxValue, new Bonus
                    {
                        Template = bonus,
                        Value = Bonus.ToRuntimeValue(bonus.Value)
                    });
                }
            }

            trg.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.AttackedEtc);
            caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.AttackEtc);

            if (target.Buffs.CheckDamageImmune(DamageType))
            {
                TraceLab("damage_skipped", caster, target,
                    $"effect={Id} reason=immune type={DamageType}");
                if (source?.Skill != null)
                    source.Skill.HitTypes[trg.ObjId] = SkillHitType.Immune;
                target.BroadcastPacket(new SCUnitDamagedPacket(castObj, casterObj, caster.ObjId, target.ObjId, 1, 0)
                {
                    HitType = SkillHitType.Immune
                }, false);
                return;
            }

            var weapon = caster?.Equipment.GetItemBySlot(WeaponSlotId);
            var holdable = (WeaponTemplate)weapon?.Template;

            var hitType = SkillHitType.Invalid;
            if (source?.Skill != null &&
                !source.Skill.HitTypes.TryGetValue(trg.ObjId, out hitType))
            {
                // Direct skills pre-roll in Skill.ApplyEffects. Plot-only
                // skills do not traverse that path, so their DamageEffect is
                // the authoritative place to perform the one native roll.
                hitType = source.Skill.RollCombatDice(caster, trg);
                source.Skill.HitTypes[trg.ObjId] = hitType;
            }

            if (source?.Skill != null && source.Skill.SkillMissed(trg.ObjId))
            {
                TraceLab("damage_skipped", caster, target,
                    $"effect={Id} reason=miss hit={hitType}");
                var missPacket = new SCUnitDamagedPacket(castObj, casterObj, caster.ObjId, target.ObjId, 0, 0)
                {
                    HoldableId = (byte)(holdable?.HoldableTemplate?.Id ?? 0),
                    HitType = hitType
                };
                // TODO: Gotta figure out how to tell if it should be applied on getting hit, or on hitting
                trg.CombatBuffs.TriggerCombatBuffs(caster, trg, hitType, false);
                caster.CombatBuffs.TriggerCombatBuffs(caster, trg, hitType, false);
                caster.BroadcastPacket(missPacket, true);
                return;
            }

            float flexibilityRateMod = trg.Flexibility / 1000 * 3;
            var combatStats = CombatStatOverrideManager.Instance;
            switch (DamageType)
            {
                case DamageType.Melee:
                    if (Rand.Next(0f, 100f) < combatStats.Resolve(
                        caster,
                        CombatStatKind.MeleeCritical,
                        caster.MeleeCritical) - flexibilityRateMod)
                        hitType = SkillHitType.MeleeCritical;
                    else
                        hitType = SkillHitType.MeleeHit;
                    break;
                case DamageType.Magic:
                    if (Rand.Next(0f, 100f) < combatStats.Resolve(
                        caster,
                        CombatStatKind.SpellCritical,
                        caster.SpellCritical) - flexibilityRateMod)
                        hitType = SkillHitType.SpellCritical;
                    else
                        hitType = SkillHitType.SpellHit;
                    break;
                case DamageType.Ranged:
                    if (Rand.Next(0f, 100f) < combatStats.Resolve(
                        caster,
                        CombatStatKind.RangedCritical,
                        caster.RangedCritical) - flexibilityRateMod)
                        hitType = SkillHitType.RangedCritical;
                    else
                        hitType = SkillHitType.RangedHit;
                    break;
                case DamageType.Siege:
                    hitType = SkillHitType.RangedHit;//No siege type?
                    break;
                default:
                    hitType = SkillHitType.Invalid;
                    break;
            }

            if (source?.Skill != null)
                source.Skill.HitTypes[trg.ObjId] = hitType;

            // The native client uses the current skillset level here, not the
            // internal rank of the Skill object.
            var skillTemplate = source.Skill?.Template;
            var abilityLevel = skillTemplate != null
                ? caster.GetAbLevel((AbilityType)skillTemplate.AbilityId)
                : caster.Level;

            // UnitAttribute 0x57 is the aggregate AA8 spell-DPS attribute. The
            // legacy server model keeps its weapon and formula portions apart.
            var dpsInc = 0;
            switch (DamageType)
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

            var weaponDps = 0;
            var damageScale = 0;

            if (UseMainhandWeapon)
            {
                weaponDps += caster.Dps;
                var mainhand = caster.Equipment.GetItemBySlot((int)EquipmentItemSlot.Mainhand);
                damageScale = (mainhand?.Template as WeaponTemplate)?.HoldableTemplate?.DamageScale ?? damageScale;
            }
            if (UseOffhandWeapon)
            {
                weaponDps += caster.OffhandDps;
                var offhand = caster.Equipment.GetItemBySlot((int)EquipmentItemSlot.Offhand);
                damageScale = (offhand?.Template as WeaponTemplate)?.HoldableTemplate?.DamageScale ?? damageScale;
            }
            if (UseRangedWeapon)
            {
                weaponDps += caster.RangedDps;
                var ranged = caster.Equipment.GetItemBySlot((int)EquipmentItemSlot.Ranged);
                damageScale = (ranged?.Template as WeaponTemplate)?.HoldableTemplate?.DamageScale ?? damageScale;
            }

            var globalDamageMultiplier = 1f;
            switch (DamageType)
            {
                case DamageType.Melee:
                    globalDamageMultiplier = caster.MeleeDamageMul;
                    break;
                case DamageType.Magic:
                    globalDamageMultiplier = caster.SpellDamageMul;
                    break;
                case DamageType.Ranged:
                    globalDamageMultiplier = caster.RangedDamageMul;
                    break;
            }

            var baseRange = DamageEffectCalculator.CalculateBaseDamageRange(
                UseFixedDamage,
                FixedMin,
                FixedMax,
                UseLevelDamage,
                caster.LevelDps,
                abilityLevel,
                skillTemplate?.AbilityLevel ?? abilityLevel,
                skillTemplate?.CastingInc ?? 0,
                LevelMd,
                LevelVaStart,
                LevelVaEnd,
                dpsInc,
                DpsIncMultiplier,
                weaponDps,
                DpsMultiplier,
                skillTemplate?.CastingTime ?? 0,
                damageScale,
                Multiplier,
                globalDamageMultiplier);
            float min = baseRange.Min;
            float max = baseRange.Max;

            if (source.Skill != null)
            {
                min = (float)caster.SkillModifiersCache.ApplyModifiers(source.Skill, SkillAttribute.Damage, min);
                max = (float)caster.SkillModifiersCache.ApplyModifiers(source.Skill, SkillAttribute.Damage, max);
            }

            if (source.Buff?.TickEffects.Count > 0)
            {
                var tickRatio = source.Buff.Duration > 0
                    ? (float)source.Buff.Tick / source.Buff.Duration
                    : 1f;
                min *= tickRatio;
                max *= tickRatio;

                caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamageEtcDot);
                trg.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamagedEtcDot);

                if (DamageType == DamageType.Magic)
                {
                    caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamageSpellDot);
                    trg.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamagedSpellDot);
                }
            }
            
            if (UseChargedBuff && source.Skill != null)
            {
                var effect = caster.Buffs.GetEffectFromBuffId(ChargedBuffId);
                var charges = effect?.Charge ?? 0;
                
                min += charges * (ChargedMul + source.Skill.Level * ChargedLevelMul);
                max += charges * (ChargedMul + source.Skill.Level * ChargedLevelMul);
                effect?.Exit();
            }

            if (UseTargetChargedBuff && source.Skill != null)
            {
                var effect = target.Buffs.GetEffectFromBuffId(TargetChargedBuffId);
                var charges = effect?.Charge ?? 0;
                
                min += charges * TargetChargedMul;
                max += charges * TargetChargedMul;
                effect?.Exit();
            }

            if (AdjustDamageByHeight)
            {
                var heightDifference = caster.Transform.World.Position.Z
                    - trg.Transform.World.Position.Z;
                var heightMultiplier = DamageEffectCalculator.CalculateHeightMultiplier(
                    heightDifference);
                min *= heightMultiplier;
                max *= heightMultiplier;
            }

            if (AdjustDamageByRange)
            {
                var distance = caster.GetDistanceTo(trg, true);
                var rangeMultiplier = DamageEffectCalculator.CalculateRangeMultiplier(
                    distance,
                    OptimumRange,
                    RangeDamageMultiplier);
                min *= rangeMultiplier;
                max *= rangeMultiplier;
            }
            
            var finalDamage = Rand.Next(min, max);

            if (castObj is CastPlot plotCast)
                finalDamage *= plotCast.GetAoeDiminishingMultiplier(trg.ObjId);
            
            // Buff tag increase (Hellspear's impale combo, for ex)
            if (TargetBuffTagId > 0 && target.Buffs.CheckBuffTag(TargetBuffTagId))
            {
                finalDamage += TargetBuffBonus;
                finalDamage *= TargetBuffBonusMul;
            }

            //toughness reduction (PVP Only)
            if (caster is Character && trg is Character)
                finalDamage *= 1 - trg.BattleResist / ( 8000f + trg.BattleResist );

            //Do Critical Dmgs
            switch (hitType)
            {
                case SkillHitType.MeleeCritical:
                    finalDamage *= 1 + (caster.MeleeCriticalBonus - trg.Flexibility / 100) / 100;
                    break;
                case SkillHitType.RangedCritical:
                    finalDamage *= 1 + (caster.RangedCriticalBonus - trg.Flexibility / 100) / 100;
                    break;
                case SkillHitType.SpellCritical:
                    finalDamage *= 1 + (caster.SpellCriticalBonus - trg.Flexibility / 100) / 100;
                    break;
                default:
                    break;
            }

            // Reduction
            var reductionMul = 1.0f;

            if (target is Unit targetUnit)
            {
                float armor;
                switch (DamageType)
                {
                    case DamageType.Melee:
                        armor = Math.Max(0f, targetUnit.Armor - caster.DefensePenetration);
                        reductionMul = 1.0f - armor / (armor + 5300.0f);
                        finalDamage = finalDamage * targetUnit.IncomingMeleeDamageMul;
                        break;
                    case DamageType.Ranged:
                        armor = Math.Max(0f, targetUnit.Armor - caster.DefensePenetration);
                        reductionMul = 1.0f - armor / (armor + 5300.0f);
                        finalDamage = finalDamage * targetUnit.IncomingRangedDamageMul;
                        break;
                    case DamageType.Magic:
                        armor = Math.Max(0f, targetUnit.MagicResistance - caster.MagicPenetration);
                        reductionMul = 1.0f - armor / (armor + 5300.0f);
                        finalDamage = finalDamage * targetUnit.IncomingSpellDamageMul;
                        break;
                    default:
                        finalDamage = finalDamage * targetUnit.IncomingDamageMul;
                        break;
                }
            }
            var value = (int)(finalDamage * reductionMul);
            var absorbed = (int)(finalDamage * (1.0f - reductionMul));
            var healthStolen = (int)(value * (HealthStealRatio / 100.0f));
            var manaStolen = (int)(value * (ManaStealRatio / 100.0f));

            //Safeguard to prevent accidental flagging
            if (!caster.CanAttack(trg))
            {
                TraceLab("damage_skipped", caster, target,
                    $"effect={Id} reason=cannot_attack relation={caster.GetRelationStateTo(trg)} value={value}");
                return;
            }

            TraceLab("damage_calculated", caster, target,
                $"effect={Id} skill={source?.Skill?.Template?.Id ?? 0} type={DamageType} hit={hitType} min={min:F3} max={max:F3} final={finalDamage:F3} reduction={reductionMul:F3} value={value}");
            var hpBefore = trg.Hp;
            trg.ReduceCurrentHp(caster, value);
            caster.SummarizeDamage[0] += value;

            NativeSkillLiveTrace.RecordDamage(
                NativeSkillLiveTrace.ResolveOriginSkill(source?.Skill, castObj),
                caster,
                trg,
                Id,
                DamageType.ToString(),
                value,
                absorbed,
                hpBefore,
                trg.Hp,
                ShouldBroadcastDamagePacket(castObj));

            if (healthStolen > 0 || manaStolen > 0)
            {
                caster.Hp = Math.Min(caster.MaxHp, caster.Hp + healthStolen);
                caster.Mp = Math.Min(caster.MaxMp, caster.Mp + manaStolen);
                caster.BroadcastPacket(new SCUnitPointsPacket(caster.ObjId, caster.Hp, caster.Mp), true);
            }


            if (Bonuses != null)
            {
                caster.Bonuses[uint.MaxValue] = new List<Bonus>();
            }

            if (Crime && caster.GetRelationStateTo(trg) == RelationState.Friendly)
            {
                if (!trg.Buffs.CheckBuff((uint)BuffConstants.Retribution))
                {
                    caster.SetCriminalState(true);
                }
            }

            // TODO : Use proper chance kinds (melee, magic etc.)
            var trgCharacter = trg as Character;
            var attacker = caster as Character;
            if (trgCharacter != null)
            {
                trgCharacter.IsInCombat = true;
                trgCharacter.LastCombatActivity = DateTime.UtcNow;
                if (attacker != null)
                {
                    trgCharacter.SetHostileActivity(attacker);
                }
                trgCharacter.Procs.RollProcsForKind(ProcChanceKind.TakeDamageAny);
            }    
            if (attacker != null)
            {
                attacker.IsInCombat = true;
                attacker.LastCombatActivity = DateTime.UtcNow;
                attacker.Procs.RollProcsForKind(ProcChanceKind.HitAny);
            }

            // TODO: Gotta figure out how to tell if it should be applied on getting hit, or on hitting
            caster.CombatBuffs.TriggerCombatBuffs(caster, target as Unit, hitType, false);
            target.CombatBuffs.TriggerCombatBuffs(caster, target as Unit, hitType, false);
            var packet = new SCUnitDamagedPacket(castObj, casterObj, caster.ObjId, target.ObjId, value, absorbed)
            {
                HoldableId = (byte)(holdable?.HoldableTemplate?.Id ?? 0),
                HitType = hitType
            };
            
            if (ShouldBroadcastDamagePacket(castObj))
            {
                if (packetBuilder != null)
                    packetBuilder.AddPacket(packet);
                else
                    trg.BroadcastPacket(packet, true);
            }

            // A lethal DamageEffect has already completed Unit.DoDie here,
            // including the AA8 ordered aggro clear. Re-publishing a positive
            // aggro table for that dead NPC reopens the closed combat lifecycle
            // and makes the r558734 client terminate its game session.
            if (trg is Npc && trg.Hp > 0 && ShouldBroadcastAggroPacket(castObj))
            {
                var aggroPacket = new SCUnitAiAggroPacket(
                    trg.ObjId,
                    1,
                    caster.ObjId,
                    caster.SummarizeDamage);

                // Direct AoE skills collect their damage notifications in a
                // DD04 packet. Publishing aggro immediately made the client
                // observe the consequence before the corresponding damage
                // entries and consistently stopped its C2S stream on AA8.
                // Preserve the causal order inside the same packet batch.
                if (packetBuilder != null)
                    packetBuilder.AddPacket(aggroPacket);
                else
                    trg.BroadcastPacket(aggroPacket, true);
            }
            if (trg is Npc npc && trg.Hp > 0/* && npc.CurrentTarget != caster*/)
            {
                npc.OnDamageReceived(caster, value);
            }

            //Invoke even if damage is 0
            caster.Events.OnAttack(this, new OnAttackArgs
            {
                Attacker = caster,
                Target = trg,
                Amount = value,
                DamageType = DamageType,
                SourceSkill = source.Skill,
                IsTriggeredEffect = source.IsTrigger,
                IsPeriodicEffect = source.Buff?.Tick > 0
            });
            trg.Events.OnAttacked(this, new OnAttackedArgs { });

            if (value > 0)
            {
                source.Skill?.ApplyHitCooldownReductions(caster, trg);
                caster.PassiveProcs.TriggerDamageSkillHit(caster, source.Skill, MechanicsRuntime.UtcNow);
                caster.Events.OnDamage(this, new OnDamageArgs {
                    Attacker = caster,
                    Target = trg,
                    Amount = value
                });
                caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamageEtc);
                trg.Events.OnDamaged(this, new OnDamagedArgs
                {
                    Attacker = caster,
                    Amount = value
                });

                switch (DamageType)
                {
                    case DamageType.Melee:
                        trg.Events.OnDamagedMelee(this, new OnDamagedArgs
                        {
                            Attacker = caster,
                            Amount = value
                        });
                        break;
                    case DamageType.Ranged:
                        trg.Events.OnDamagedRanged(this, new OnDamagedArgs
                        {
                            Attacker = caster,
                            Amount = value
                        });
                        break;
                    case DamageType.Magic:
                        trg.Events.OnDamagedSpell(this, new OnDamagedArgs
                        {
                            Attacker = caster,
                            Amount = value
                        });
                        break;
                    case DamageType.Siege:
                        trg.Events.OnDamagedSiege(this, new OnDamagedArgs
                        {
                            Attacker = caster,
                            Amount = value
                        });
                        break;
                }
                
                trg.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.DamagedEtc);
            }
        }

        private static bool ShouldBroadcastAggroPacket(CastAction castAction)
        {
            // AA8 live isolation V18: keep authoritative NPC aggro/AI updates
            // in OnDamageReceived, but do not publish the client-side aggro
            // table for Plot impacts or periodic CastBuff ticks. Direct
            // CastSkill impacts remain the positive control.
            return !(castAction is CastBuff) && !(castAction is CastPlot);
        }

        private static void TraceLab(string eventName, BaseUnit actor, BaseUnit target, string detail)
        {
            MechanicsRuntime.Current?.EventSink?.RecordEvent(
                eventName,
                actor?.ObjId ?? 0,
                target?.ObjId ?? 0,
                detail);
        }

        private static bool ShouldBroadcastDamagePacket(CastAction castAction)
        {
            // The AA8 CastBuff body is confirmed by the native reader. The
            // disconnect isolated in V18 was caused by publishing periodic
            // entries as independent envelopes; BuffTemplate now restores the
            // native per-tick DD04 transaction boundary.
            return true;
        }
    }
}
