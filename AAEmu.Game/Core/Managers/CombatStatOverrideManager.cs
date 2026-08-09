using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System;

using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Managers
{
    /// <summary>
    /// Session-only combat-stat overrides used by controlled GM diagnostics.
    /// These values are deliberately kept outside buffs, equipment and MySQL.
    /// </summary>
    public class CombatStatOverrideManager : Singleton<CombatStatOverrideManager>, ICombatStatOverrideService
    {
        private readonly ConcurrentDictionary<(uint ObjId, CombatStatKind Stat), float> _overrides =
            new ConcurrentDictionary<(uint ObjId, CombatStatKind Stat), float>();

        public void Set(Unit unit, CombatStatKind stat, float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || value < 1f || value > 100f)
                throw new ArgumentOutOfRangeException(nameof(value), "Combat-stat overrides must be between 1 and 100.");

            _overrides[(unit.ObjId, stat)] = value;
        }

        public bool TryGet(Unit unit, CombatStatKind stat, out float value)
        {
            return _overrides.TryGetValue((unit.ObjId, stat), out value);
        }

        public bool Clear(Unit unit, CombatStatKind stat)
        {
            return _overrides.TryRemove((unit.ObjId, stat), out _);
        }

        public void ClearAll(Unit unit)
        {
            foreach (var key in _overrides.Keys.Where(key => key.ObjId == unit.ObjId))
                _overrides.TryRemove(key, out _);
        }

        public float Resolve(Unit unit, CombatStatKind stat, float baseValue)
        {
            return TryGet(unit, stat, out var value) ? value : baseValue;
        }

        public float GetBaseValue(Unit unit, CombatStatKind stat)
        {
            switch (stat)
            {
                case CombatStatKind.MeleeAccuracy:
                    return unit.MeleeAccuracy;
                case CombatStatKind.RangedAccuracy:
                    return unit.RangedAccuracy;
                case CombatStatKind.SpellAccuracy:
                    return unit.SpellAccuracy;
                case CombatStatKind.MeleeCritical:
                    return unit.MeleeCritical;
                case CombatStatKind.RangedCritical:
                    return unit.RangedCritical;
                case CombatStatKind.SpellCritical:
                    return unit.SpellCritical;
                case CombatStatKind.HealCritical:
                    return unit.HealCritical;
                case CombatStatKind.MeleeParry:
                    return unit.MeleeParryRate;
                case CombatStatKind.RangedParry:
                    return unit.RangedParryRate;
                case CombatStatKind.Block:
                    return unit.BlockRate;
                case CombatStatKind.Dodge:
                    return unit.DodgeRate;
                default:
                    return 0f;
            }
        }

        public float GetDirectNativeBonus(Unit unit, CombatStatKind stat)
        {
            UnitAttribute attribute;
            switch (stat)
            {
                case CombatStatKind.MeleeAccuracy:
                    attribute = UnitAttribute.MeleeAntiMissMul;
                    break;
                case CombatStatKind.RangedAccuracy:
                    attribute = UnitAttribute.RangedAntiMissMul;
                    break;
                case CombatStatKind.SpellAccuracy:
                    attribute = UnitAttribute.SpellAntiMissMul;
                    break;
                case CombatStatKind.MeleeCritical:
                    attribute = UnitAttribute.MeleeCriticalMul;
                    break;
                case CombatStatKind.RangedCritical:
                    attribute = UnitAttribute.RangedCriticalMul;
                    break;
                case CombatStatKind.SpellCritical:
                    attribute = UnitAttribute.SpellCriticalMul;
                    break;
                case CombatStatKind.HealCritical:
                    attribute = UnitAttribute.HealCriticalMul;
                    break;
                case CombatStatKind.MeleeParry:
                    attribute = UnitAttribute.MeleeParryMul;
                    break;
                case CombatStatKind.RangedParry:
                    attribute = UnitAttribute.RangedParryMul;
                    break;
                case CombatStatKind.Block:
                    attribute = UnitAttribute.BlockMul;
                    break;
                case CombatStatKind.Dodge:
                    attribute = UnitAttribute.DodgeMul;
                    break;
                default:
                    return 0f;
            }

            // AA8 stores these direct percentage-point modifiers in tenths.
            // Starting from zero mirrors Character's calculation: Percent
            // modifiers do not invent a base value, while Value modifiers add.
            double rawValue = 0d;
            foreach (var bonus in unit.GetBonuses(attribute))
            {
                if (bonus.Template.ModifierType == UnitModifierType.Percent)
                    rawValue += rawValue * bonus.Value / 100f;
                else
                    rawValue += bonus.Value;
            }
            return (float)(rawValue / 10d);
        }

        public IReadOnlyDictionary<CombatStatKind, float> GetOverrides(Unit unit)
        {
            return _overrides
                .Where(entry => entry.Key.ObjId == unit.ObjId)
                .ToDictionary(entry => entry.Key.Stat, entry => entry.Value);
        }

        public bool ShouldTrace(Unit unit)
        {
            if (_overrides.Keys.Any(key => key.ObjId == unit.ObjId))
                return true;

            return unit.Buffs.CheckBuff(404)
                || unit.Buffs.CheckBuff(7651)
                || unit.Buffs.CheckBuff(13612)
                || unit.Buffs.CheckBuff(13613);
        }
    }
}
