using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemAwakeningCalculatorTests
{
    private static readonly GradeTemplate[] Grades =
    [
        new() { Grade = 1, GradeOrder = 0 },
        new() { Grade = 0, GradeOrder = 1 },
        new() { Grade = 2, GradeOrder = 2 },
        new() { Grade = 3, GradeOrder = 3 },
        new() { Grade = 4, GradeOrder = 4 },
        new() { Grade = 5, GradeOrder = 5 }
    ];

    [Test]
    public async Task ExplorerNodachiRankOne_UsesR575RouteAndLandsAtGrand()
    {
        // compact r575 group 48: Explorer's Nodachi 47784 at Arcane -> Radiant 47894.
        var group = new ItemChangeMappingGroup { Id = 48, Success = 10000, EvolvingExpInherit = true };
        group.Mappings.Add(new ItemChangeMapping
        {
            Id = 900,
            MappingGroupId = 48,
            SourceItemId = 47784,
            TargetItemId = 47894,
            SourceGradeId = 4,
            TargetGradeId = -1
        });

        var route = ItemAwakeningCalculator.SelectMapping(group, 47784, 4, 900);
        await Assert.That(route).IsNotNull();
        await Assert.That(route.TargetItemId).IsEqualTo(47894u);

        // Source category 636 pays 14 + 21 + 28 = 63 EXP to reach Arcane. Target category 646
        // charges 63 at Basic, so replaying that inherited total lands exactly at Grand with 0 left.
        var source = new ItemRndAttrCategory { Id = 636 };
        source.Properties[0] = new() { GradeId = 0, GradeExp = 14 };
        source.Properties[2] = new() { GradeId = 2, GradeExp = 21 };
        source.Properties[3] = new() { GradeId = 3, GradeExp = 28 };
        source.Properties[4] = new() { GradeId = 4, GradeExp = 0 };

        var target = new ItemRndAttrCategory { Id = 646 };
        target.Properties[0] = new() { GradeId = 0, GradeExp = 63 };
        target.Properties[2] = new() { GradeId = 2, GradeExp = 139 };

        var totalOk = ItemAwakeningCalculator.TryCalculateTotalExperience(
            source, 4, 0, Grades, out var totalExperience);
        var gradeOk = ItemSynthesisCalculator.TryResolveGrades(
            target,
            0,
            0,
            totalExperience,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var resultGrade,
            out var remainingExperience);

        await Assert.That(totalOk).IsTrue();
        await Assert.That(totalExperience).IsEqualTo(63);
        await Assert.That(gradeOk).IsTrue();
        await Assert.That(resultGrade).IsEqualTo((byte)2);
        await Assert.That(remainingExperience).IsEqualTo(0);
    }

    [Test]
    public async Task PreferredRoute_MustBelongToGroupAndMatchSourceGrade()
    {
        var group = new ItemChangeMappingGroup { Id = 48 };
        group.Mappings.Add(new ItemChangeMapping
        {
            Id = 1, MappingGroupId = 48, SourceItemId = 47784, TargetItemId = 47894, SourceGradeId = 4
        });
        group.Mappings.Add(new ItemChangeMapping
        {
            Id = 2, MappingGroupId = 49, SourceItemId = 47784, TargetItemId = 99999, SourceGradeId = 4
        });

        var selected = ItemAwakeningCalculator.SelectMapping(group, 47784, 4, 2);
        var wrongGrade = ItemAwakeningCalculator.SelectMapping(group, 47784, 3, 1);

        await Assert.That(selected.Id).IsEqualTo(1u);
        await Assert.That(wrongGrade).IsNull();
    }

    [Test]
    public async Task Chance_UsesBasisPointsAndWholePercentPity()
    {
        var group = new ItemChangeMappingGroup { Success = 1000 };
        var chance = ItemAwakeningCalculator.SuccessChance(group, 4);

        await Assert.That(chance).IsEqualTo(1400);
        await Assert.That(ItemAwakeningCalculator.IsSuccess(chance, 1399)).IsTrue();
        await Assert.That(ItemAwakeningCalculator.IsSuccess(chance, 1400)).IsFalse();
    }

    [Test]
    public async Task AwakeningTemperLoss_UsesNativeFloorAndInclusiveRange()
    {
        await Assert.That(ItemAwakeningCalculator.ResolveTemperAfterSuccess(25, 20, 0, 2, 2))
            .IsEqualTo((ushort)23);
        await Assert.That(ItemAwakeningCalculator.ResolveTemperAfterSuccess(21, 20, 0, 2, 2))
            .IsEqualTo((ushort)20);
        await Assert.That(ItemAwakeningCalculator.ResolveTemperAfterSuccess(20, 20, 0, 2, 2))
            .IsEqualTo((ushort)20);
        await Assert.That(ItemAwakeningCalculator.ResolveTemperAfterSuccess(25, 0, 0, 0, 0))
            .IsEqualTo((ushort)25);
        await Assert.That(ItemAwakeningCalculator.ResolveTemperAfterSuccess(25, 20, 1, 1, 1))
            .IsEqualTo((ushort)24);
    }
}
