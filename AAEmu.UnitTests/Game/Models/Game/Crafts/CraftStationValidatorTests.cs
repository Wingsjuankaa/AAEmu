using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.UnitTests.Game.Models.Game.Crafts;

public class CraftStationValidatorTests
{
    private static Craft BoundTaxes()
    {
        // r575: craft 76 -> canonical plate 2392; plate 9405 / phase 26178 offers pack 3.
        var craft = new Craft { Id = 76, ReqDoodadId = 2392 };
        craft.CraftPackIds.Add(3);
        return craft;
    }

    [Test]
    public async Task ResidentialPlateAcceptsItsNativeTaxCatalogue()
    {
        var accepted = CraftStationValidator.TryValidate(
            BoundTaxes(), true, 9405, DoodadFuncPermission.Owner, out var failure,
            [new(3, DoodadFuncPermission.Public)]);
        await Assert.That(accepted).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
    }

    [Test]
    public async Task DifferentOrMissingCatalogueDoesNotMakeStationEquivalent()
    {
        foreach (var offers in new CraftStationOffer[][] { [], [new(4, DoodadFuncPermission.Public)] })
        {
            var accepted = CraftStationValidator.TryValidate(
                BoundTaxes(), true, 9405, DoodadFuncPermission.Public, out var failure, offers);
            await Assert.That(accepted).IsFalse();
            await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
        }
    }

    [Test]
    public async Task CatalogueCannotAuthorizeAMissingStation()
    {
        var accepted = CraftStationValidator.TryValidate(
            BoundTaxes(), false, 9405, DoodadFuncPermission.Public, out var failure,
            [new(3, DoodadFuncPermission.Public)]);
        await Assert.That(accepted).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
    }

    [Test]
    public async Task NonTaxCatalogueDoesNotBypassHousingDenialOrRevocation()
    {
        var craft = BoundTaxes();
        craft.Id = 123; // Even an unrelated recipe in pack 3 must not inherit the tax exception.
        CraftStationOffer[] offers = [new(3, DoodadFuncPermission.Public)];
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 9405, DoodadFuncPermission.Public, out _, offers, true)).IsTrue();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 9405, DoodadFuncPermission.Public, out var failure, offers, false)).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
    }

    [Test]
    public async Task BothTaxRecipesArePublicOnCanonicalAndAlternativePrivateNameplates()
    {
        foreach (var recipeId in new uint[] { 76, 9267 })
        foreach (var templateId in new uint[] { 2392, 9405 })
        {
            var craft = BoundTaxes();
            craft.Id = recipeId;
            var accepted = CraftStationValidator.TryValidate(
                craft, true, templateId, DoodadFuncPermission.Owner, out var failure,
                [new(3, DoodadFuncPermission.Public)], false);
            await Assert.That(accepted).IsTrue();
            await Assert.That(failure).IsEqualTo(CraftFailure.None);
        }
    }

    [Test]
    public async Task TaxExceptionRequiresLivePublicTaxOfferEvenOnCanonicalNameplate()
    {
        foreach (var recipeId in new uint[] { 76, 9267 })
        foreach (var offers in new CraftStationOffer[][]
                 { [], [new(3, DoodadFuncPermission.Owner)], [new(4, DoodadFuncPermission.Public)] })
        {
            var craft = BoundTaxes();
            craft.Id = recipeId;
            craft.CraftPackIds.Add(4);
            var accepted = CraftStationValidator.TryValidate(
                craft, true, 2392, DoodadFuncPermission.Public, out var failure, offers, false);
            await Assert.That(accepted).IsFalse();
            await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
        }
    }

    [Test]
    public async Task TaxExceptionRejectsChangedRecipeStationOrCatalogueMembership()
    {
        var craft = BoundTaxes();
        craft.ReqDoodadId = 42;
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Public, out var failure,
            [new(3, DoodadFuncPermission.Public)], false)).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);

        craft.ReqDoodadId = 2392;
        craft.CraftPackIds.Clear();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 2392, DoodadFuncPermission.Public, out failure,
            [new(3, DoodadFuncPermission.Public)], false)).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
    }

    [Test]
    public async Task TaxExceptionIsRevalidatedWhenPublicPhaseEnds()
    {
        var craft = BoundTaxes();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 2392, DoodadFuncPermission.Owner, out _,
            [new(3, DoodadFuncPermission.Public)], false)).IsTrue();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 2392, DoodadFuncPermission.Public, out var failure, [], false)).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
        await Assert.That(CraftStationValidator.TryValidate(
            craft, false, 2392, DoodadFuncPermission.Public, out failure,
            [new(3, DoodadFuncPermission.Public)], false)).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
    }

    [Test]
    public async Task MatchingFunctionPermissionWinsOverUnrelatedPublicFunction()
    {
        var accepted = CraftStationValidator.TryValidate(
            BoundTaxes(), true, 9405, DoodadFuncPermission.Public, out var failure,
            [new(3, DoodadFuncPermission.Owner), new(4, DoodadFuncPermission.Public)]);
        await Assert.That(accepted).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
    }

    [Test]
    public async Task LeavingCraftingPhaseRevokesAlternativeStation()
    {
        var craft = BoundTaxes();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 9405, DoodadFuncPermission.Public, out _,
            [new(3, DoodadFuncPermission.Public)])).IsTrue();
        await Assert.That(CraftStationValidator.TryValidate(
            craft, true, 9405, DoodadFuncPermission.Public, out var failure, [])).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
    }

    [Test]
    public async Task RequiredStationMustExistAndMatchExactly()
    {
        var craft = new Craft { ReqDoodadId = 42 };

        var missing = CraftStationValidator.TryValidate(
            craft, false, 0, null, out var missingFailure);
        var wrong = CraftStationValidator.TryValidate(
            craft, true, 41, DoodadFuncPermission.Public, out var wrongFailure);
        var correct = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Public, out var correctFailure);

        await Assert.That(missing).IsFalse();
        await Assert.That(missingFailure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
        await Assert.That(wrong).IsFalse();
        await Assert.That(wrongFailure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
        await Assert.That(correct).IsTrue();
        await Assert.That(correctFailure).IsEqualTo(CraftFailure.None);
    }

    [Test]
    public async Task UnprovenPermissionModesFailClosed()
    {
        var craft = new Craft { ReqDoodadId = 42 };

        var accepted = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Public, out _);
        var rejected = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Owner, out var failure);

        await Assert.That(accepted).IsTrue();
        await Assert.That(rejected).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
    }
}
