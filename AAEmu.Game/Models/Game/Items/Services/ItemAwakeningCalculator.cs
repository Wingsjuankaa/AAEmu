using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>Pure validation and arithmetic shared by awakening runtime code and regressions.</summary>
internal static class ItemAwakeningCalculator
{
    internal const int ChanceScale = 10000;

    internal static ItemChangeMapping SelectMapping(
        ItemChangeMappingGroup group,
        uint sourceItemId,
        byte sourceGrade,
        uint preferredMappingId)
    {
        if (group is null || sourceItemId == 0)
            return null;

        bool Matches(ItemChangeMapping mapping) =>
            mapping.MappingGroupId == group.Id &&
            mapping.SourceItemId == sourceItemId &&
            (mapping.SourceGradeId < 0 || mapping.SourceGradeId == sourceGrade);

        if (preferredMappingId != 0)
        {
            var preferred = group.Mappings.FirstOrDefault(mapping => mapping.Id == preferredMappingId);
            if (preferred is not null && Matches(preferred))
                return preferred;
        }

        return group.Mappings.FirstOrDefault(Matches);
    }

    internal static int SuccessChance(ItemChangeMappingGroup group, byte mappingFailBonus)
    {
        if (group is null)
            return 0;
        return Math.Clamp(group.Success + mappingFailBonus * 100, 0, ChanceScale);
    }

    internal static bool IsSuccess(int chance, int roll)
    {
        if (roll is < 0 or >= ChanceScale)
            throw new ArgumentOutOfRangeException(nameof(roll));
        return Math.Clamp(chance, 0, ChanceScale) > roll;
    }

    /// <summary>
    /// Total EXP represented by a source item: every paid grade below its current one plus the EXP
    /// currently stored in its bar. Grades are ordered by grade_order, never by their numeric id.
    /// </summary>
    internal static bool TryCalculateTotalExperience(
        ItemRndAttrCategory category,
        byte currentGrade,
        int currentExperience,
        IEnumerable<GradeTemplate> grades,
        out int totalExperience)
    {
        totalExperience = currentExperience;
        if (category is null || grades is null || currentExperience < 0)
            return false;

        var foundCurrentGrade = false;
        try
        {
            foreach (var grade in grades.Where(entry => entry is not null).OrderBy(entry => entry.GradeOrder))
            {
                if (grade.Grade == currentGrade)
                {
                    foundCurrentGrade = true;
                    break;
                }

                totalExperience = checked(totalExperience +
                    (category.GetProperty((byte)grade.Grade)?.GradeExp ?? 0));
            }
        }
        catch (OverflowException)
        {
            return false;
        }

        return foundCurrentGrade;
    }
}
