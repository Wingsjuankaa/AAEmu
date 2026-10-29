namespace AAEmu.Game.Models.Game.Skills;

/// <summary>
/// One r575 <c>skill_reqs</c> row. <c>default_result</c> chooses whether the row applies
/// to linked or unlinked skills; an applicable row blocks only while its buff or tag is present.
/// </summary>
public readonly record struct SkillRequirement(
    uint Id, bool OnTarget, uint BuffId, uint BuffTagId, bool DefaultResult, string Message);

/// <summary>
/// The r575 client first selects skill requirement rows by their skill/skill-tag links, then tests
/// applicable rows against the caster or target's buffs. x2game.dll release SHA-256
/// 2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76:
/// FUN_39689570 at RVA 0x689570, membership FUN_39b96780 at RVA 0xb96780,
/// and target-kind gate FUN_39b941f0 at RVA 0xb941f0.
/// </summary>
public static class SkillRequirementRules
{
    /// <summary>
    /// Native selector: <c>default_result='t'</c> applies only to skills named by
    /// <c>skill_req_skills</c> or <c>skill_req_skill_tags</c>; <c>'f'</c> applies to all
    /// other skills. Links on an <c>'f'</c> row exempt that skill from a general restriction.
    /// </summary>
    public static bool Applies(bool defaultResult, bool linked) => defaultResult == linked;

    public static IReadOnlyList<SkillRequirement> SelectApplicable(
        IReadOnlyList<SkillRequirement> rows, IReadOnlySet<uint> linkedRequirementIds,
        SkillTargetType targetType = SkillTargetType.Self)
    {
        if (rows == null || rows.Count == 0)
            return [];

        var selected = new List<SkillRequirement>();
        foreach (var row in rows)
            if ((!row.OnTarget || !HasNonUnitTarget(targetType)) &&
                Applies(row.DefaultResult, linkedRequirementIds?.Contains(row.Id) ?? false))
                selected.Add(row);
        return selected;
    }

    /// <summary>Native target-kind gate: target-side buff checks do not apply to these target types.</summary>
    public static bool HasNonUnitTarget(SkillTargetType targetType) => targetType is
        SkillTargetType.Pos or SkillTargetType.Line or SkillTargetType.Doodad or SkillTargetType.Item or
        SkillTargetType.BallisticPos or SkillTargetType.SummonPos or SkillTargetType.RelativePos or
        SkillTargetType.SourcePos or SkillTargetType.ArtilleryPos or SkillTargetType.CursorPos or
        SkillTargetType.CommanderPos;

    /// <summary>An applicable row fails only when its named buff or buff tag is present.</summary>
    public static bool AllowsCast(
        IReadOnlyList<SkillRequirement> requirements,
        Func<SkillRequirement, bool> carriesBuff,
        Func<SkillRequirement, bool> carriesBuffTag,
        out string message)
    {
        message = null;
        if (requirements == null)
            return true;

        foreach (var requirement in requirements)
        {
            if (requirement.BuffId > 0 && (carriesBuff?.Invoke(requirement) ?? false) ||
                requirement.BuffTagId > 0 && (carriesBuffTag?.Invoke(requirement) ?? false))
            {
                message = requirement.Message;
                return false;
            }
        }
        return true;
    }
}
