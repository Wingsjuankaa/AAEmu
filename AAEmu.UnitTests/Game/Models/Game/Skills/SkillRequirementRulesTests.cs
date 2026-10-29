using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillRequirementRulesTests
{
    private static SkillRequirement Row(uint id, uint tag, bool defaultResult = false) =>
        new(id, false, 0, tag, defaultResult, $"row {id}");

    private static bool Allows(IReadOnlyList<SkillRequirement> requirements, params uint[] tags)
    {
        var active = tags.ToHashSet();
        return SkillRequirementRules.AllowsCast(requirements, _ => false,
            requirement => active.Contains(requirement.BuffTagId), out _);
    }

    [Test]
    public async Task DefaultFalseRow_IsGlobalRestrictionWithLinkedSkillsExempted()
    {
        // r575 skill_reqs 58 is restraint tag 4981, default_result='f'.
        // Defiance 39036 links it explicitly, so that state cannot reject Defiance.
        var rows = new[] { Row(58, 4981) };
        var defiance = SkillRequirementRules.SelectApplicable(rows, new HashSet<uint> { 58 });
        var ordinarySkill = SkillRequirementRules.SelectApplicable(rows, new HashSet<uint>());

        await Assert.That(defiance).IsEmpty();
        await Assert.That(Allows(defiance, 4981)).IsTrue();
        await Assert.That(ordinarySkill.Count).IsEqualTo(1);
        await Assert.That(Allows(ordinarySkill, 4981)).IsFalse();
        await Assert.That(Allows(ordinarySkill)).IsTrue();
    }

    [Test]
    public async Task DefaultTrueRow_AppliesOnlyToLinkedSkills()
    {
        var rows = new[] { Row(1, 27, true) };
        var linked = SkillRequirementRules.SelectApplicable(rows, new HashSet<uint> { 1 });
        var unlinked = SkillRequirementRules.SelectApplicable(rows, new HashSet<uint>());

        await Assert.That(linked.Count).IsEqualTo(1);
        await Assert.That(Allows(linked, 27)).IsFalse();
        await Assert.That(unlinked).IsEmpty();
    }

    [Test]
    public async Task SelectorUsesEitherSkillOrSkillTagLink_AndPreservesRowOrder()
    {
        // The loader unions explicit skill-id links and expanded skill-tag links before selection.
        var rows = new[] { Row(25, 0), Row(58, 4981), Row(330, 4194), Row(402, 0, true) };
        var linkedIds = new HashSet<uint> { 25, 58, 330, 402 };
        var selected = SkillRequirementRules.SelectApplicable(rows, linkedIds);

        await Assert.That(selected.Select(row => row.Id)).IsEquivalentTo(new uint[] { 402 });
    }

    [Test]
    public async Task ApplicableRowsRejectOnlyPresentBuffOrTagAndReturnNativeMessage()
    {
        var requirements = new[]
        {
            new SkillRequirement(21, true, 1729, 0, true, "target carries buff"),
            Row(58, 4981)
        };

        await Assert.That(SkillRequirementRules.AllowsCast(requirements,
            requirement => requirement.BuffId == 1729, _ => false, out var message)).IsFalse();
        await Assert.That(message).IsEqualTo("target carries buff");
        await Assert.That(Allows(requirements, 4981)).IsFalse();
        await Assert.That(Allows(requirements)).IsTrue();
    }

    [Test]
    public async Task TargetSideRowsAreSkippedForNativeNonUnitTargets()
    {
        var targetRow = new SkillRequirement(21, true, 1729, 0, false, "target buff");
        var casterRow = Row(58, 4981);
        var rows = new[] { targetRow, casterRow };

        var position = SkillRequirementRules.SelectApplicable(rows, null, SkillTargetType.Pos);
        var hostile = SkillRequirementRules.SelectApplicable(rows, null, SkillTargetType.Hostile);
        await Assert.That(position.Select(row => row.Id)).IsEquivalentTo(new uint[] { 58 });
        await Assert.That(hostile.Select(row => row.Id)).IsEquivalentTo(new uint[] { 21, 58 });
    }

    [Test]
    public async Task NoRowsAllowCast()
    {
        await Assert.That(SkillRequirementRules.SelectApplicable([], null)).IsEmpty();
        await Assert.That(SkillRequirementRules.AllowsCast(null, _ => true, _ => true, out _)).IsTrue();
    }
}
