using System.Collections.Generic;

using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Managers
{
    public enum CombatStatKind
    {
        MeleeAccuracy,
        RangedAccuracy,
        SpellAccuracy,
        MeleeCritical,
        RangedCritical,
        SpellCritical,
        HealCritical,
        MeleeParry,
        RangedParry,
        Block,
        Dodge
    }

    public interface ICombatStatOverrideService
    {
        void Set(Unit unit, CombatStatKind stat, float value);
        bool TryGet(Unit unit, CombatStatKind stat, out float value);
        bool Clear(Unit unit, CombatStatKind stat);
        void ClearAll(Unit unit);
        float Resolve(Unit unit, CombatStatKind stat, float baseValue);
        float GetBaseValue(Unit unit, CombatStatKind stat);
        float GetDirectNativeBonus(Unit unit, CombatStatKind stat);
        IReadOnlyDictionary<CombatStatKind, float> GetOverrides(Unit unit);
    }
}
