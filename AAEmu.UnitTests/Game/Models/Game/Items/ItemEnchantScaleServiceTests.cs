using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemEnchantScaleServiceTests
{
    [Test]
    public async Task NativeAa10Item_StartsAtNoneAndNormalTemperAdvancesToPlusOne()
    {
        var service = NewService();
        var item = NewWeapon(scale: 0);

        var created = service.TryCreateAttempt(item, (int)TemperTargetKind.Weapon, false, 30, 0,
            out var attempt, out var failure);
        var outcome = service.ResolveOutcome(attempt, 0, 1);

        await Assert.That(created).IsTrue();
        await Assert.That(failure).IsEmpty();
        await Assert.That(attempt.BeforeScaleId).IsEqualTo((ushort)0);
        await Assert.That(outcome.Result).IsEqualTo(ItemRefurbishmentResult.Success);
        await Assert.That(outcome.AfterScaleId).IsEqualTo((ushort)1);
    }

    [Test]
    public async Task ShiningTemper_GreatSuccessAdvancesTwoButClampsAtTemplateCap()
    {
        var service = NewService();
        var item = NewWeapon(scale: 29);

        var created = service.TryCreateAttempt(item, (int)TemperTargetKind.Weapon, true, 30, 0,
            out var attempt, out _);
        var outcome = service.ResolveOutcome(attempt, 0, 1);

        await Assert.That(created).IsTrue();
        await Assert.That(outcome.Result).IsEqualTo(ItemRefurbishmentResult.GreatSuccess);
        await Assert.That(outcome.AfterScaleId).IsEqualTo((ushort)30);
    }

    [Test]
    public async Task PlusTwelve_RemainsTemperableTowardRetailPlusThirtyCap()
    {
        var service = NewService();
        var item = NewWeapon(scale: 12);

        var created = service.TryCreateAttempt(item, (int)TemperTargetKind.Weapon, false, 30, 0,
            out var attempt, out var failure);

        await Assert.That(created).IsTrue();
        await Assert.That(failure).IsEmpty();
        await Assert.That(attempt.BeforeScaleId).IsEqualTo((ushort)12);
        await Assert.That(attempt.SuccessScaleId).IsEqualTo((ushort)13);
    }

    [Test]
    public async Task TemplateCapCatalystCapAndForbidCatalogue_AreEnforced()
    {
        var service = NewService();
        var capped = NewWeapon(scale: 30);
        var forbidden = NewWeapon(scale: 0, templateId: 70000);
        service.RegisterForbiddenItem(forbidden.TemplateId);

        var cappedCreated = service.TryCreateAttempt(capped, (int)TemperTargetKind.Weapon, false, 30, 0,
            out _, out _);
        var forbiddenCreated = service.TryCreateAttempt(forbidden, (int)TemperTargetKind.Weapon, false, 30, 0,
            out _, out _);

        await Assert.That(cappedCreated).IsFalse();
        await Assert.That(forbiddenCreated).IsFalse();
    }

    [Test]
    public async Task ScaleMultiplier_UsesRetailPerMilleScale()
    {
        var service = NewService();

        await Assert.That(service.GetMultiplier(0)).IsEqualTo(1d);
        await Assert.That(service.GetMultiplier(12)).IsEqualTo(1.12d);
    }

    [Test]
    public async Task WeaponCharm_MultiplierFiftyMeansOnePointFiveTimesSuccess()
    {
        var ratio = new EnchantScaleRatio
        {
            SuccessRatio = 2530,
            DownRatio = 5000
        };
        var charm = new ItemGradeEnchantingSupport { AddSuccessMul = 50 };

        var probabilities = ItemEnchantScaleService.NormalizeProbabilities(ratio, charm, false);

        await Assert.That(probabilities.SuccessRatio).IsEqualTo(3795);
        await Assert.That(probabilities.DowngradeRatio).IsEqualTo(3102);
        await Assert.That(probabilities.FailRatio).IsEqualTo(3103);
    }

    [Test]
    public async Task AnchoringCharm_RemovesDowngradeAndResplendentVariantDoublesSuccess()
    {
        var ratio = new EnchantScaleRatio
        {
            SuccessRatio = 2530,
            DownRatio = 5000
        };
        var charm = new ItemGradeEnchantingSupport
        {
            AddSuccessMul = 100,
            AddDowngradeMul = -100
        };

        var probabilities = ItemEnchantScaleService.NormalizeProbabilities(ratio, charm, false);

        await Assert.That(probabilities.SuccessRatio).IsEqualTo(5060);
        await Assert.That(probabilities.DowngradeRatio).IsEqualTo(0);
        await Assert.That(probabilities.FailRatio).IsEqualTo(4940);
    }

    private static ItemEnchantScaleService NewService()
    {
        var service = new ItemEnchantScaleService();
        for (ushort id = 0; id < ItemEnchantScaleService.NativeRatioCount; id++)
        {
            service.Register(new EnchantScaleRatio
            {
                Id = id,
                Name = id == 0 ? "none" : $"+{id}",
                Scale = Math.Min(id, (ushort)30) * 10,
                SuccessRatio = id < 10 ? 10000 : 8570,
                GreatSuccessRatio = 2000,
                Cost = id + 1
            });
        }
        service.MarkNativeCatalogueAvailable();
        return service;
    }

    private static Weapon NewWeapon(ushort scale, uint templateId = 60000)
    {
        var template = new WeaponTemplate
        {
            Id = templateId,
            Level = 55,
            MaxEnchantScaleId = 30,
            HoldableTemplate = new Holdable { SlotTypeId = 4 }
        };
        // The runtime constructor resolves durability through ItemManager's DI singleton. These
        // service tests only need the native item kind and template metadata, so keep the fixture
        // independent from the application container.
        return new Weapon
        {
            Id = 1,
            TemplateId = templateId,
            Template = template,
            Count = 1,
            ScaledA = scale
        };
    }
}
