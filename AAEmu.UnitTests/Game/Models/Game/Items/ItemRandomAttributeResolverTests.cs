using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemRandomAttributeResolverTests
{
    [Test]
    public async Task Synthesis_PreservesExistingEffectAndRollsOnlyNewSlot()
    {
        var category = Category(748, 3, 2);
        var main = Set(category, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 1, 3));
        var bonus = Set(category, 509, 1,
            Group(3911, 509, 77, 3),
            Group(3912, 509, 82, 3));

        var result = ItemRandomAttributeResolver.ResolveForSynthesis(
            category, 3, [main.Groups[1].Id], _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.GroupIds.SequenceEqual([3907u, 3911u])).IsTrue();
        await Assert.That(result.AddedGroupIds.SequenceEqual([3911u])).IsTrue();
    }

    [Test]
    public async Task ExplorerRankTwo_MapsFirstStatAndAddsSecond()
    {
        var source = Category(648, 4, 1);
        Set(source, 327, 1,
            Group(2584, 327, 0, 4),
            Group(2585, 327, 1, 4));

        var target = Category(748, 3, 2);
        Set(target, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 1, 3));
        Set(target, 509, 1,
            Group(3911, 509, 77, 3),
            Group(3912, 509, 82, 3));

        var result = ItemRandomAttributeResolver.ResolveForAwakening(
            source, target, 3, [2585u], _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.GroupIds.SequenceEqual([3907u, 3911u])).IsTrue();
        await Assert.That(result.AddedGroupIds.SequenceEqual([3911u])).IsTrue();
    }

    [Test]
    public async Task HiramAwakening_MapsFarmedStatsAndAddsOnlyThird()
    {
        var source = Category(748, 5, 2);
        Set(source, 508, 1,
            Group(3907, 508, 1, 5));
        Set(source, 509, 1,
            Group(3911, 509, 77, 5));

        var hiram = Category(497, 4, 3);
        Set(hiram, 102, 1,
            Group(1198, 102, 1, 4));
        Set(hiram, 114, 2,
            Group(1271, 114, 77, 4),
            Group(1272, 114, 82, 4));

        var result = ItemRandomAttributeResolver.ResolveForAwakening(
            source, hiram, 4, [3907u, 3911u], _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.GroupIds.SequenceEqual([1198u, 1271u, 1272u])).IsTrue();
        await Assert.That(result.AddedGroupIds.SequenceEqual([1272u])).IsTrue();
    }

    [Test]
    public async Task SameCategoryMapping_KeepsIdsInsteadOfFollowingLaterInheritanceSet()
    {
        var category = Category(599, 4, 1);
        var set = Set(category, 252, 1, Group(2085, 252, 1, 4));
        set.InheritPriorityId = 439;

        var result = ItemRandomAttributeResolver.ResolveForAwakening(
            category, category, 4, [2085u], _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.GroupIds.SequenceEqual([2085u])).IsTrue();
        await Assert.That(result.AddedGroupIds.Count).IsEqualTo(0);
    }

    [Test]
    public async Task RandomReroll_ReplacesOnlyRequestedSlotUsingWeights()
    {
        var category = Category(748, 3, 2);
        var main = Set(category, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 1, 3),
            Group(3908, 508, 2, 3));
        main.Groups[2].Weight = 3;
        Set(category, 509, 1, Group(3911, 509, 77, 3));

        // Candidates are 3907(weight 1), then 3908(weight 3). Roll 1 enters the second range.
        var result = ItemRandomAttributeResolver.ResolveReroll(
            category, 3, [3906u, 3911u], 0, 0, _ => 1);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.Before.Id).IsEqualTo(3906u);
        await Assert.That(result.After.Id).IsEqualTo(3908u);
        await Assert.That(result.GroupIds.SequenceEqual([3908u, 3911u])).IsTrue();
    }

    [Test]
    public async Task SelectableReroll_HonoursLegalExplicitGroup()
    {
        var category = Category(748, 3, 1);
        Set(category, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 1, 3));

        var result = ItemRandomAttributeResolver.ResolveReroll(
            category, 3, [3906u], 0, 3907, _ => throw new InvalidOperationException("RNG must not run"));

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.GroupIds.SequenceEqual([3907u])).IsTrue();
    }

    [Test]
    public async Task Reroll_RejectsOccupiedAttributeAndWrongSet()
    {
        var category = Category(748, 3, 2);
        Set(category, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 77, 3),
            Group(3908, 508, 82, 3));
        Set(category, 509, 1, Group(3911, 509, 77, 3));

        var occupied = ItemRandomAttributeResolver.ResolveReroll(
            category, 3, [3906u, 3911u], 0, 3907, _ => 0);
        var wrongSet = ItemRandomAttributeResolver.ResolveReroll(
            category, 3, [3906u, 3911u], 0, 3911, _ => 0);

        await Assert.That(occupied.IsValid).IsFalse();
        await Assert.That(wrongSet.IsValid).IsFalse();
    }

    [Test]
    public async Task Reroll_RejectsOutOfRangePhysicalIndex()
    {
        var category = Category(748, 3, 1);
        Set(category, 508, 1,
            Group(3906, 508, 0, 3),
            Group(3907, 508, 1, 3));

        var result = ItemRandomAttributeResolver.ResolveReroll(
            category, 3, [3906u], 1, 0, _ => 0);

        await Assert.That(result.IsValid).IsFalse();
    }

    private static ItemRndAttrCategory Category(uint id, byte grade, int maximum)
    {
        var category = new ItemRndAttrCategory { Id = id, Name = id.ToString() };
        category.Properties[grade] = new ItemRndAttrCategoryProperty
        {
            CategoryId = id,
            GradeId = grade,
            MaxUnitModifierNum = maximum
        };
        return category;
    }

    private static ItemRndAttrUnitModifierGroupSet Set(
        ItemRndAttrCategory category,
        uint id,
        int pickNum,
        params ItemRndAttrUnitModifierGroup[] groups)
    {
        var set = new ItemRndAttrUnitModifierGroupSet
        {
            Id = id,
            CategoryId = category.Id,
            Name = id.ToString(),
            PickNum = pickNum
        };
        set.Groups.AddRange(groups);
        category.GroupSets.Add(set);
        return set;
    }

    private static ItemRndAttrUnitModifierGroup Group(
        uint id,
        uint setId,
        uint attribute,
        byte grade)
    {
        var group = new ItemRndAttrUnitModifierGroup
        {
            Id = id,
            GroupSetId = setId,
            UnitAttributeId = attribute,
            UnitModifierTypeId = 0,
            Weight = 1
        };
        group.ValueByGrade[grade] = 1;
        return group;
    }
}
