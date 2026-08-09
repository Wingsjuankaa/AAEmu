using System;
using AAEmu.Commons.Utils;
using System.Collections.Generic;
using System.Linq;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Utils;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Plots
{
    public class PlotCondition
    {
        protected static Logger _log = LogManager.GetCurrentClassLogger();
        public uint Id { get; set; }
        public bool NotCondition { get; set; }
        public PlotConditionType Kind { get; set; }
        public int Param1 { get; set; }
        public int Param2 { get; set; }
        public int Param3 { get; set; }
        public int Param4 { get; set; }
        public bool Pure { get; set; }
        public bool OrUnitReqs { get; set; }
        public List<SkillUnitRequirement> UnitRequirements { get; } =
            new List<SkillUnitRequirement>();

        public bool Check(BaseUnit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject, PlotEventCondition eventCondition, Skill skill)
        {
            var res = true;
            switch (Kind)
            {
                case PlotConditionType.Level:
                    res = ConditionLevel(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2, Param3);
                    break;
                case PlotConditionType.Relation:
                    res = ConditionRelation(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2, Param3);
                    break;
                case PlotConditionType.Direction:
                    res = ConditionDirection(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2, Param3, eventCondition);
                    break;
                case PlotConditionType.BuffTag:
                    res = ConditionBuffTag(caster, casterCaster, target, targetCaster, skillObject,
                        Param1, Param2, Param3, Param4, eventCondition);
                    break;
                case PlotConditionType.WeaponEquipStatus:
                    res = ConditionWeaponEquipStatus(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2, Param3); 
                    break;
                case PlotConditionType.Chance:
                    res = ConditionChance(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Dead:
                    res = ConditionDead(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.CombatDiceResult:
                    res = ConditionCombatDiceResult(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3, skill); // Every CombatDiceResult is a NotCondition -> false makes it true. 
                    break;
                case PlotConditionType.InstrumentType:
                    res = ConditionInstrumentType(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Range:
                    res = ConditionRange(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Variable:
                    res = ConditionVariable(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2, Param3);
                    break;
                case PlotConditionType.UnitAttrib:
                    res = ConditionUnitAttrib(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Actability:
                    res = ConditionActability(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Stealth:
                    res = ConditionStealth(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.Visible:
                    res = ConditionVisible(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.ABLevel:
                    res = ConditionABLevel(caster, casterCaster, target, targetCaster, skillObject, Param1, Param2,
                        Param3);
                    break;
                case PlotConditionType.CastingUseable:
                    res = ConditionCastingUseable(caster, Param1, Param2);
                    break;
                case PlotConditionType.UnitReqs:
                    res = ConditionUnitRequirements(target);
                    break;
            }

            _log.Trace("PlotCondition : {0} | Params : {1}, {2}, {3} | Result : {4}", Kind, Param1, Param2, Param3, NotCondition ? !res : res);            

            return NotCondition ? !res : res;
        }

        private static bool ConditionLevel(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int minLevel, int maxLevel, int unk3)
        {
            return caster is Unit unitCaster && unitCaster.Level >= minLevel && unitCaster.Level <= maxLevel;
        }

        private static bool ConditionRelation(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int relationType, int unk2, int unk3)
        {
            if (caster == null || target == null)
                return false;

            // AA8 stores the same relation ids used by skill targeting in
            // plot_conditions.param1. In particular, Hammer Toss uses
            // relation 5 (Others) with not_condition=1 to distinguish the
            // original target from nearby targets: only the original target
            // receives the stun, while the others follow the knockback path.
            return SkillTargetingUtil.IsRelationValid((SkillTargetRelation)relationType, caster, target);
        }

        private static bool ConditionDirection(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3, PlotEventCondition eventCondition)
        {
            return MathUtil.IsFront(caster, target);
        }

        private static bool ConditionBuffTag(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int tagId, int unk2,
            int minimumStack, int maximumStack, PlotEventCondition eventCondition)
        {
            if (target == null)
                return false;

            var taggedBuffs = SkillManager.Instance.GetBuffsByTagId((uint)tagId);
            var stack = target.Buffs.GetBuffStackCount(taggedBuffs);
            return MatchesBuffStackRange(stack, minimumStack, maximumStack);
        }

        public static bool MatchesBuffStackRange(
            int stack,
            int minimumStack,
            int maximumStack)
        {
            if (stack <= 0)
                return false;
            if (minimumStack > 0 && stack < minimumStack)
                return false;
            if (maximumStack > 0 && stack > maximumStack)
                return false;
            return true;
        }

        private static bool ConditionWeaponEquipStatus(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int weaponEquipStatus, int unk2, int unk3)
        {
            if (caster is Character character)
            {
                var hasRangedWeapon =
                    character.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Ranged)?.Template
                    is WeaponTemplate;
                return MatchesWeaponEquipStatus(
                    weaponEquipStatus,
                    character.GetWeaponWieldKind(),
                    hasRangedWeapon);
            }
            return false;
        }

        public static bool MatchesWeaponEquipStatus(
            int weaponEquipStatus,
            WeaponWieldKind wieldKind,
            bool hasRangedWeapon)
        {
            switch ((PlotWeaponEquipStatus)weaponEquipStatus)
            {
                case PlotWeaponEquipStatus.OneHanded:
                    return wieldKind == WeaponWieldKind.OneHanded;
                case PlotWeaponEquipStatus.TwoHanded:
                    return wieldKind == WeaponWieldKind.TwoHanded;
                case PlotWeaponEquipStatus.DualWielded:
                    return wieldKind == WeaponWieldKind.DuelWielded;
                case PlotWeaponEquipStatus.Ranged:
                    return hasRangedWeapon;
                default:
                    return false;
            }
        }
        
        private static bool ConditionChance(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int chance, int unk2, int unk3)
        {
            // Param2 is only used once, and its value is "1"
            var roll = Rand.Next(0, 100);
            return roll <= chance;
        }
        
        private static bool ConditionDead(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3)
        {
            // Positional plot targets are synthetic BaseUnit instances. They
            // have no alive/dead state, so the positive Dead condition is
            // false and a native NotCondition correctly evaluates to true.
            return target is Unit unitTarget && unitTarget.Hp == 0;
        }
        
        private static bool ConditionCombatDiceResult(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3, Skill skill)
        {
            if (caster is Unit unitCaster && target is Unit trg && skill != null)
            {
                // DamageEffect owns the native combat-dice roll and records
                // the final hit/critical/miss result.  Conditions must reuse
                // that result: rolling here again lets damage and the plot
                // branch disagree.  A condition can still appear before a
                // damage effect, so keep one lazy roll as a safe fallback.
                if (!skill.HitTypes.TryGetValue(trg.ObjId, out var hitType))
                {
                    hitType = skill.RollCombatDice(unitCaster, trg);
                    skill.HitTypes[trg.ObjId] = hitType;
                }

                return MatchesCombatDiceResult(unk1, hitType);
            }
            return false;
        }

        /// <summary>
        /// AA8 plot_conditions.param1 is a bit mask over the native
        /// combat_dice_result domain: bit 0=hit, 1=critical, 2=miss,
        /// 3=dodge, 4=block, 5=parry, 6=resist, 7=immune.
        /// </summary>
        public static bool MatchesCombatDiceResult(int resultMask, SkillHitType hitType)
        {
            var resultId = CombatDiceResultId(hitType);
            if (resultId == 0)
                return false;

            return (resultMask & (1 << (resultId - 1))) != 0;
        }

        private static int CombatDiceResultId(SkillHitType hitType)
        {
            switch (hitType)
            {
                case SkillHitType.MeleeHit:
                case SkillHitType.RangedHit:
                case SkillHitType.SpellHit:
                    return 1;
                case SkillHitType.MeleeCritical:
                case SkillHitType.RangedCritical:
                case SkillHitType.SpellCritical:
                    return 2;
                case SkillHitType.MeleeMiss:
                case SkillHitType.RangedMiss:
                case SkillHitType.SpellMiss:
                    return 3;
                case SkillHitType.MeleeDodge:
                case SkillHitType.RangedDodge:
                    return 4;
                case SkillHitType.MeleeBlock:
                case SkillHitType.RangedBlock:
                    return 5;
                case SkillHitType.MeleeParry:
                case SkillHitType.RangedParry:
                    return 6;
                case SkillHitType.SpellResist:
                    return 7;
                case SkillHitType.Immune:
                    return 8;
                default:
                    return 0;
            }
        }
        
        private static bool ConditionInstrumentType(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int instrumentTypeId, int unk2, int unk3)
        {
            // Param1 is either 21, 22 or 23
            if (caster is Character character)
            {
                var item = character.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Musical);
                if (item == null)
                    return false;
                if (item.Template is WeaponTemplate template)
                {
                    if (instrumentTypeId == template.HoldableTemplate.SlotTypeId)
                        return true;
                }
            }
            return false;
        }
        
        private static bool ConditionRange(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int minRange, int maxRange, int unk3)
        {
            // Param1 = Min range
            // Param2 = Max range
            if (!(caster is Unit unitCaster) || target == null)
                return false;

            var range = unitCaster.GetDistanceTo(target);
            return MatchesRange(range, minRange, maxRange);
        }

        public static bool MatchesRange(float edgeDistance, int minRange, int maxRange)
        {
            return edgeDistance >= minRange && edgeDistance <= maxRange;
        }
        
        private static bool ConditionVariable(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3)
        {
            if (!(caster is Unit unitCaster))
                return false;

            var state = unitCaster.ActivePlotState;
            if (!PlotVariableOperations.TryResolve(state, unk1, out var variableValue))
            {
                _log.Error("Invalid Plot Variable operand[{0}]", unk1);
                return false;
            }

            if (PlotVariableOperations.TryCompare(variableValue, unk2, unk3, out var result))
                return result;

            _log.Error("Invalid Plot Variable Condition Operation[{0}]", unk2);
            return false;
        }
        
        private static bool ConditionUnitAttrib(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3)
        {
            // All 3 params used. No idea.
            return true;
        }

        private static bool ConditionActability(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int actabilityId, int op, int level)
        {
            // Check actability level
            // Param1 = Actability ID
            // Param2 = Operator (2, 3, 5) for equal, less than and less than or equal
            // Param3 = Actability Level
            return true;
        }
        
        private static bool ConditionStealth(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3)
        {
            return target?.Buffs?.HasStealth() == true;
        }
        
        private static bool ConditionVisible(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int unk1, int unk2, int unk3)
        {
            return caster?.UnitIsVisible(target) == true;
        }
        private static bool ConditionABLevel(BaseUnit caster, SkillCaster casterCaster, BaseUnit target,
            SkillCastTarget targetCaster, SkillObject skillObject, int abilityType, int min, int max)
        {
            if (caster is Character character)
            {
                var ability = character.Abilities.Abilities[(AbilityType)abilityType];
                int abLevel = ExpirienceManager.Instance.GetLevelFromExp(ability.Exp);
                return abLevel >= min && abLevel <= max;
            }
            //Should this ever not be a character using this condition?
            return false;
        }

        private static bool ConditionCastingUseable(
            BaseUnit caster,
            int minimumPercent,
            int maximumPercent)
        {
            var state = (caster as Unit)?.ActivePlotState;
            return state != null &&
                   state.CastingPercent >= minimumPercent &&
                   state.CastingPercent <= maximumPercent;
        }

        private bool ConditionUnitRequirements(BaseUnit target)
        {
            if (!(target is Unit targetUnit) || UnitRequirements.Count == 0)
                return false;

            var results = UnitRequirements.Select(requirement =>
                requirement.IsTargetSupported && requirement.ValidateTarget(targetUnit));
            return OrUnitReqs ? results.Any(result => result) : results.All(result => result);
        }
    }
}
