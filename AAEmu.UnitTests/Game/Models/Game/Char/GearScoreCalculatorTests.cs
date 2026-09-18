using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class GearScoreCalculatorTests
{
    [Test]
    public async Task Augmentations_UseOwnLevels_AndFrostIsNotRepeatedForSockets()
    {
        var equipment = new EquipItem(1, new WeaponTemplate { Id = 1, Level = 71 }, 1);
        equipment.GemData[0] = 999; // image, never a bonus
        equipment.GemData[1] = 10; // frost
        equipment.GemData[3] = 999; // synthesis XP, never a bonus
        equipment.GemData[13] = 999; // synthesis attribute, never a bonus
        equipment.SetNativeSocket(0, 20);
        equipment.SetNativeSocket(8, 21);
        equipment.SetNativeSocket(1, 404); // unresolved template is ignored
        var templates = new Dictionary<uint, ItemTemplate>
        {
            [10] = new ItemTemplate { Level = 17 },
            [20] = new ItemTemplate { Level = 23 },
            [21] = new ItemTemplate { Level = 31 }
        };
        var calls = new List<(FormulaKind, int)>();
        var score = GearScoreCalculator.AddAugmentations(100f, equipment,
            id => templates.GetValueOrDefault(id), (kind, level) =>
            {
                calls.Add((kind, level));
                return level + 0.19;
            });
        await Assert.That(calls.ToArray()).IsEquivalentTo(new[] {
            (FormulaKind.GearScoreEnchantingGem, 17),
            (FormulaKind.GearScoreSocket, 23), (FormulaKind.GearScoreSocket, 31)
        });
        await Assert.That(Math.Abs(score - 171.3f) < 0.0001f).IsTrue();
    }

    [Test]
    public async Task NativeComponent_FloorsOneDecimalInsteadOfRounding()
    {
        await Assert.That(GearScoreCalculator.NativeComponent(168.68776261371724)).IsEqualTo(168.6f);
        await Assert.That(GearScoreCalculator.NativeComponent(34.499392663970184)).IsEqualTo(34.4f);
        await Assert.That(GearScoreCalculator.NativeComponent(100)).IsEqualTo(100f);
    }

    [Test]
    public async Task NativeUnitScore_ExcludesFaceHairAndNonScoredSpecialSlots()
    {
        var slots = Enumerable.Range(0, 34).Where(GearScoreCalculator.IsScoredSlot).ToArray();
        await Assert.That(slots).IsEquivalentTo(Enumerable.Range(0, 19).Concat(new[] {26, 27, 29, 30, 32}).ToArray());
        await Assert.That(GearScoreCalculator.IsScoredSlot(-1)).IsFalse();
        await Assert.That(GearScoreCalculator.IsScoredSlot(34)).IsFalse();
    }

    [Test]
    public async Task StoredMultiplier_IsHundredthsOfTheFormulaMultiplier()
    {
        // A weapon the table weighs 2.2, an armor slot it weighs 0.78.
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(220)).IsEqualTo(2.2);
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(78)).IsEqualTo(0.78);
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(330)).IsEqualTo(3.3);
    }

    [Test]
    public async Task StoredMultiplier_CosmeticTiersLandOnTheValuesTheArmorFormulaComparesAgainst()
    {
        // Formula 56 branches on gear_score_multiplier - 0.01 and - 0.02 for the two cosmetic tiers,
        // which the table stores as 1 and 2.
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(1)).IsEqualTo(0.01);
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(2)).IsEqualTo(0.02);
    }

    [Test]
    public async Task StoredMultiplier_MissingRowStaysZero()
    {
        await Assert.That(GearScoreCalculator.FromStoredMultiplier(0)).IsEqualTo(0.0);
    }
}
