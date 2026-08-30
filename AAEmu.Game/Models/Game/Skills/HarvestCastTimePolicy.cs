using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;

namespace AAEmu.Game.Models.Game.Skills;

/// <summary>
/// Applies the custom harvest speed only when the AA10 doodad graph proves that
/// the triggered use transitions directly into a loot-only phase.
/// </summary>
internal static class HarvestCastTimePolicy
{
    private const int MinimumWireCastTimeMilliseconds = 10;

    public static int Apply(int castTimeMilliseconds, double configuredRate, Doodad target, uint skillId)
    {
        if (castTimeMilliseconds <= 0 || target == null ||
            !IsNativeHarvestTransition(target, skillId))
            return castTimeMilliseconds;

        return ApplyRate(castTimeMilliseconds, configuredRate);
    }

    internal static int ApplyRate(int castTimeMilliseconds, double configuredRate)
    {
        if (castTimeMilliseconds <= 0 || !double.IsFinite(configuredRate) || configuredRate <= 0d)
            return castTimeMilliseconds;

        return Math.Max(
            MinimumWireCastTimeMilliseconds,
            (int)Math.Round(castTimeMilliseconds / configuredRate));
    }

    internal static bool IsNativeHarvestTransition(Doodad target, uint skillId)
    {
        var manager = DoodadManager.Instance;
        var currentFunc = manager.GetFunc(target.FuncGroupId, skillId);
        if (currentFunc == null || currentFunc.NextPhase <= 0)
            return false;

        var currentTemplate = manager.GetFuncTemplate(currentFunc.FuncId, currentFunc.FuncType);
        if (currentTemplate is not DoodadFuncUse useTemplate ||
            (currentFunc.SkillId != skillId && useTemplate.SkillId != skillId))
            return false;

        var nextFuncs = manager.GetFuncsForGroup((uint)currentFunc.NextPhase);
        return IsNativeHarvestTransition(currentFunc, useTemplate, nextFuncs);
    }

    internal static bool IsNativeHarvestTransition(
        DoodadFunc currentFunc,
        DoodadFuncUse currentTemplate,
        IReadOnlyCollection<DoodadFunc> nextFuncs)
    {
        return currentFunc is { NextPhase: > 0 } &&
               currentTemplate != null &&
               nextFuncs is { Count: > 0 } &&
               nextFuncs.All(func => Doodad.IsFuncDrivenLootFunc(func.FuncType));
    }
}
