using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemSynthesisCalculatorTests
{
    private static readonly GradeTemplate[] Grades =
    [
        new() { Grade = 1, GradeOrder = 0 }, // Crude sorts before Basic although its id is higher.
        new() { Grade = 0, GradeOrder = 1 }, // Basic
        new() { Grade = 2, GradeOrder = 2 }, // Grand
        new() { Grade = 3, GradeOrder = 3 }, // Rare
        new() { Grade = 4, GradeOrder = 4 }, // Arcane
        new() { Grade = 5, GradeOrder = 5 }, // Heroic
        new() { Grade = 6, GradeOrder = 6 }, // Unique
        new() { Grade = 7, GradeOrder = 7 }, // Celestial
        new() { Grade = 8, GradeOrder = 8 }, // Divine
        new() { Grade = 9, GradeOrder = 9 }, // Epic
        new() { Grade = 10, GradeOrder = 10 }, // Legendary
        new() { Grade = 11, GradeOrder = 11 }, // Mythic
        new() { Grade = 12, GradeOrder = 12 } // Eternal
    ];

    [Test]
    public async Task Aa10QuestArmorAndRankOneInfusion_ResolveUsingNativeR575Values()
    {
        // compact r575: target 48023 -> category 651; infusion 48845 -> gain_exp 50.
        // The actual quest item starts at Grand. Category 651 then costs Grand 17 and Rare 23, so a
        // single 50 EXP infusion reaches Arcane with 10 section EXP, exactly as observed in r575.
        var category = new ItemRndAttrCategory { Id = 651 };
        category.Properties[0] = new() { GradeId = 0, GradeExp = 12 };
        category.Properties[2] = new() { GradeId = 2, GradeExp = 17 };
        category.Properties[3] = new() { GradeId = 3, GradeExp = 23 };
        category.Properties[4] = new() { GradeId = 4, GradeExp = 0 };

        var ok = ItemSynthesisCalculator.TryResolveGrades(
            category,
            2,
            0,
            50,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var grade,
            out var experience);

        await Assert.That(ok).IsTrue();
        await Assert.That(grade).IsEqualTo((byte)4);
        await Assert.That(experience).IsEqualTo(10);
    }

    [Test]
    public async Task BonusFields_ArePermilleOfMaterialExperience()
    {
        var property = new ItemRndAttrCategoryProperty
        {
            GainExp = 200,
            BonusExpChance = 500,
            BonusExpMin = 150,
            BonusExpMax = 300
        };

        var triggered = ItemSynthesisCalculator.CalculateBonusExperience(200, property, 499, 250);
        var missed = ItemSynthesisCalculator.CalculateBonusExperience(200, property, 500, 250);

        await Assert.That(triggered).IsEqualTo(50);
        await Assert.That(missed).IsEqualTo(0);
    }

    [Test]
    public async Task HiramOverflow_CostsExactlyWhatTheR575PreviewDisplays()
    {
        // Regression captured on AA10 r575: Arcane Hiram Guardian Shirt 45339, category 501,
        // receives one 500,000 EXP infusion 54328. Only 21,827 EXP fits through the Celestial bar.
        // Every involved section weighs 130,000 permille, yielding 2,837,510 copper
        // (283 gold, 75 silver, 10 copper), while the remaining 478,173 EXP is free overflow.
        var category = new ItemRndAttrCategory { Id = 501, MaxEvolvingGrade = 7 };
        category.Properties[4] = new() { GradeId = 4, GradeExp = 1587, GoldMul = 130000 };
        category.Properties[5] = new() { GradeId = 5, GradeExp = 3056, GoldMul = 130000 };
        category.Properties[6] = new() { GradeId = 6, GradeExp = 5878, GoldMul = 130000 };
        category.Properties[7] = new() { GradeId = 7, GradeExp = 11306, GoldMul = 130000 };

        var ok = ItemSynthesisCalculator.TryCalculateCostValue(
            category,
            4,
            0,
            500000,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var costValue,
            out var pricedExperience);

        await Assert.That(ok).IsTrue();
        await Assert.That(pricedExperience).IsEqualTo(21827);
        await Assert.That(costValue).IsEqualTo(2837510L);
    }

    [Test]
    public async Task SynthesisCost_UsesEachTraversedGradesMultiplierAndExistingSectionExp()
    {
        var category = new ItemRndAttrCategory { Id = 999, MaxEvolvingGrade = 6 };
        category.Properties[4] = new() { GradeId = 4, GradeExp = 1000, GoldMul = 1000 };
        category.Properties[5] = new() { GradeId = 5, GradeExp = 2000, GoldMul = 2000 };
        category.Properties[6] = new() { GradeId = 6, GradeExp = 3000, GoldMul = 3000 };

        var ok = ItemSynthesisCalculator.TryCalculateCostValue(
            category,
            4,
            500,
            10000,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var costValue,
            out var pricedExperience);

        // 500 * 1 + 2,000 * 2 + 3,000 * 3; the remaining 4,500 EXP is overflow.
        await Assert.That(ok).IsTrue();
        await Assert.That(pricedExperience).IsEqualTo(5500);
        await Assert.That(costValue).IsEqualTo(13500L);
    }

    [Test]
    public async Task GradeResolution_RejectsExperienceOverflow()
    {
        var category = new ItemRndAttrCategory { Id = 1 };
        category.Properties[0] = new() { GradeId = 0, GradeExp = 10 };

        var ok = ItemSynthesisCalculator.TryResolveGrades(
            category,
            0,
            int.MaxValue,
            1,
            _ => Grades[1],
            _ => Grades[2],
            out _,
            out _);

        await Assert.That(ok).IsFalse();
    }

    [Test]
    public async Task HiramTierOne_StopsAtCelestialAndCapsOverflowInItsFinalBar()
    {
        var category = new ItemRndAttrCategory { Id = 496, MaxEvolvingGrade = 7 };
        category.Properties[6] = new() { GradeId = 6, GradeExp = 7131 };
        category.Properties[7] = new() { GradeId = 7, GradeExp = 13714 };
        category.Properties[8] = new() { GradeId = 8, GradeExp = 0 };

        var ok = ItemSynthesisCalculator.TryResolveGrades(
            category,
            6,
            0,
            500000,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var grade,
            out var experience);

        await Assert.That(ok).IsTrue();
        await Assert.That(grade).IsEqualTo((byte)7);
        await Assert.That(experience).IsEqualTo(13714);
    }

    [Test]
    public async Task HiramTierTwo_ObservedInfusionsReachDivineWithExactRemainingExperience()
    {
        // r575 category 509 (Radiant Hiram Guardian Nodachi), corrected from the stale shipped cap
        // of Celestial to Divine because awakening route 8450 requires source grade 8.
        // The observed run began Heroic at 5,632 EXP and consumed 12,500 + 30,000 + 30,000 EXP.
        var category = new ItemRndAttrCategory { Id = 509, MaxEvolvingGrade = 8 };
        category.Properties[5] = new() { GradeId = 5, GradeExp = 10390 };
        category.Properties[6] = new() { GradeId = 6, GradeExp = 19983 };
        category.Properties[7] = new() { GradeId = 7, GradeExp = 38433 };
        category.Properties[8] = new() { GradeId = 8, GradeExp = 38433 };

        var ok = ItemSynthesisCalculator.TryResolveGrades(
            category,
            5,
            5632,
            72500,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var grade,
            out var experience);

        await Assert.That(ok).IsTrue();
        await Assert.That(grade).IsEqualTo((byte)8);
        await Assert.That(experience).IsEqualTo(9326);
    }

    [Test]
    public async Task Undergarments_WithEternalCapContinuePastAFullCelestialBar()
    {
        // AA10 category 23 ships this complete ladder through Eternal. A stale cap of 7 made the
        // client and server report Celestial as Max Grade even though grades 8-12 are populated.
        var category = new ItemRndAttrCategory { Id = 23, MaxEvolvingGrade = 12 };
        category.Properties[7] = new() { GradeId = 7, GradeExp = 2100 };
        category.Properties[8] = new() { GradeId = 8, GradeExp = 2400 };
        category.Properties[9] = new() { GradeId = 9, GradeExp = 3200 };
        category.Properties[10] = new() { GradeId = 10, GradeExp = 6600 };
        category.Properties[11] = new() { GradeId = 11, GradeExp = 10000 };
        category.Properties[12] = new() { GradeId = 12, GradeExp = 15000 };

        var ok = ItemSynthesisCalculator.TryResolveGrades(
            category,
            7,
            2100,
            3200,
            id => Grades.SingleOrDefault(grade => grade.Grade == id),
            order => Grades.SingleOrDefault(grade => grade.GradeOrder == order),
            out var grade,
            out var experience);

        await Assert.That(ok).IsTrue();
        await Assert.That(grade).IsEqualTo((byte)9);
        await Assert.That(experience).IsEqualTo(800);
    }

    [Test]
    public async Task PromotedGrades_GrantChangeAttemptsUpToFive()
    {
        await Assert.That(ItemSynthesisCalculator.CalculateAddedChangeAttempts(0, 3)).IsEqualTo(3);
        await Assert.That(ItemSynthesisCalculator.CalculateAddedChangeAttempts(4, 3)).IsEqualTo(1);
        await Assert.That(ItemSynthesisCalculator.CalculateAddedChangeAttempts(5, 3)).IsEqualTo(0);
        await Assert.That(ItemSynthesisCalculator.CalculateAddedChangeAttempts(2, 0)).IsEqualTo(0);
    }
}
