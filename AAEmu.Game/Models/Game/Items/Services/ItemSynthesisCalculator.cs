using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>
/// Deterministic synthesis arithmetic shared by the runtime and regression tests.
/// </summary>
internal static class ItemSynthesisCalculator
{
    /// <summary>The r575 Gear Upgrade UI and item detail cap free Change Attempts at five.</summary>
    internal const int MaxChangeAttempts = 5;

    internal static int CalculateAddedChangeAttempts(ushort currentAttempts, int promotedGrades)
    {
        if (promotedGrades <= 0 || currentAttempts >= MaxChangeAttempts)
            return 0;
        return Math.Min(promotedGrades, MaxChangeAttempts - currentAttempts);
    }

    internal static bool TryResolveGrades(
        ItemRndAttrCategory category,
        byte startGrade,
        int currentExperience,
        int addedExperience,
        Func<int, GradeTemplate> gradeById,
        Func<int, GradeTemplate> gradeByOrder,
        out byte grade,
        out int remainingExperience)
    {
        grade = startGrade;
        remainingExperience = currentExperience;
        if (category is null || currentExperience < 0 || addedExperience < 0 ||
            gradeById is null || gradeByOrder is null)
            return false;

        try
        {
            remainingExperience = checked(currentExperience + addedExperience);
        }
        catch (OverflowException)
        {
            return false;
        }

        var maximumGrade = category.MaxEvolvingGrade >= 0
            ? gradeById(category.MaxEvolvingGrade)
            : null;

        while (true)
        {
            var required = category.GetProperty(grade)?.GradeExp ?? 0;
            if (required <= 0 || remainingExperience < required)
                break;

            var currentGrade = gradeById(grade);
            if (maximumGrade is not null && currentGrade is not null &&
                currentGrade.GradeOrder >= maximumGrade.GradeOrder)
            {
                remainingExperience = required;
                break;
            }

            var nextGrade = currentGrade is null ? null : gradeByOrder(currentGrade.GradeOrder + 1);
            if (nextGrade is null || nextGrade.Grade == grade || nextGrade.Grade is < byte.MinValue or > byte.MaxValue)
                break;

            if (maximumGrade is not null && nextGrade.GradeOrder > maximumGrade.GradeOrder)
            {
                remainingExperience = required;
                break;
            }

            remainingExperience -= required;
            grade = (byte)nextGrade.Grade;
        }

        var cap = category.GetProperty(grade)?.GradeExp ?? 0;
        if (cap > 0 && remainingExperience > cap)
            remainingExperience = cap;
        return true;
    }

    /// <summary>
    /// Resolves the native per-mille bonus fields. Both rolls are supplied by the caller so tests can
    /// pin the boundary conditions without depending on process-global randomness.
    /// </summary>
    internal static int CalculateBonusExperience(
        int materialExperience,
        ItemRndAttrCategoryProperty property,
        int chanceRoll,
        int bonusPermilleRoll)
    {
        if (materialExperience <= 0 || property is null)
            return 0;
        if (chanceRoll is < 0 or >= 1000)
            throw new ArgumentOutOfRangeException(nameof(chanceRoll));

        var chance = Math.Clamp(property.BonusExpChance, 0, 1000);
        if (chanceRoll >= chance)
            return 0;

        var minimum = Math.Clamp(Math.Min(property.BonusExpMin, property.BonusExpMax), 0, 1000);
        var maximum = Math.Clamp(Math.Max(property.BonusExpMin, property.BonusExpMax), minimum, 1000);
        if (bonusPermilleRoll < minimum || bonusPermilleRoll > maximum)
            throw new ArgumentOutOfRangeException(nameof(bonusPermilleRoll));

        return checked((int)((long)materialExperience * bonusPermilleRoll / 1000));
    }
}
