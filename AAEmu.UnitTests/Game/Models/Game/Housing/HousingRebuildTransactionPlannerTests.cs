using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingRebuildTransactionPlannerTests
{
    [Test]
    public async Task ClientTargetHousingIdSelectsTheRouteWithinTheSourcePack()
    {
        var routes = new[]
        {
            CreateRoute(),
            new HousingRebuildingRoute(15, 3, new HousingRebuildingDefinition
            {
                Id = 8,
                SkillId = 28829,
                TargetHousingId = 437,
                Materials = [new HousingRebuildingMaterial(34983, 15)]
            })
        };

        var selected = HousingRebuildingRouteSelector.FindByTargetHousingId(routes, 437);
        var internalDefinitionId = HousingRebuildingRouteSelector.FindByTargetHousingId(routes, 8);

        await Assert.That(selected).IsSameReferenceAs(routes[1]);
        await Assert.That(selected.Definition.Id).IsEqualTo(8u);
        await Assert.That(internalDefinitionId).IsNull();
    }

    [Test]
    public async Task CreatesImmutablePlanFromValidSnapshot()
    {
        var route = CreateRoute();
        var snapshot = CreateSnapshot(new Dictionary<uint, int> { [34983] = 15, [47083] = 6 });

        var accepted = HousingRebuildTransactionPlanner.TryCreate(
            snapshot, route, 28829, 15, out var plan, out var failure);

        await Assert.That(accepted).IsTrue();
        await Assert.That(failure.Reason).IsEqualTo(HousingRebuildBlockReason.None);
        await Assert.That(plan.HouseId).IsEqualTo(16u);
        await Assert.That(plan.TargetHousingId).IsEqualTo(435u);
        await Assert.That(plan.TaxCertificateCost).IsEqualTo(15);
    }

    [Test]
    public async Task AggregatesDuplicateMaterialRowsBeforeAccepting()
    {
        var route = CreateRoute([
            new HousingRebuildingMaterial(34983, 10),
            new HousingRebuildingMaterial(34983, 5)
        ]);
        var snapshot = CreateSnapshot(new Dictionary<uint, int> { [34983] = 10 });

        var accepted = HousingRebuildTransactionPlanner.TryCreate(
            snapshot, route, 28829, 15, out _, out var failure);

        await Assert.That(accepted).IsFalse();
        await Assert.That(failure.Reason).IsEqualTo(HousingRebuildBlockReason.MissingMaterials);
    }

    [Test]
    public async Task RejectsOwnerAndTaxMismatchWithoutPlan()
    {
        var route = CreateRoute();
        var snapshot = CreateSnapshot(
            new Dictionary<uint, int> { [34983] = 15, [47083] = 6 }) with
        {
            HouseOwnerId = 99
        };

        var accepted = HousingRebuildTransactionPlanner.TryCreate(
            snapshot, route, 28829, 15, out var plan, out var failure);

        await Assert.That(accepted).IsFalse();
        await Assert.That(plan).IsNull();
        await Assert.That(failure.Reason).IsEqualTo(HousingRebuildBlockReason.NotOwner);
    }

    [Test]
    public async Task PreservesCatalogueBlockReason()
    {
        var route = CreateRoute();
        route.Definition.BlockReason = HousingRebuildBlockReason.TerritorialSubsystemRequired;

        var accepted = HousingRebuildTransactionPlanner.TryCreate(
            CreateSnapshot(new Dictionary<uint, int>()), route, 28829, 0,
            out _, out var failure);

        await Assert.That(accepted).IsFalse();
        await Assert.That(failure.Reason)
            .IsEqualTo(HousingRebuildBlockReason.TerritorialSubsystemRequired);
    }

    private static HousingRebuildingRoute CreateRoute(
        IReadOnlyList<HousingRebuildingMaterial> materials = null)
    {
        var definition = new HousingRebuildingDefinition
        {
            Id = 6,
            SkillId = 28829,
            TargetHousingId = 435,
            Materials = materials ?? [
                new HousingRebuildingMaterial(34983, 15),
                new HousingRebuildingMaterial(47083, 6)
            ]
        };
        return new HousingRebuildingRoute(15, 1, definition);
    }

    private static HousingRebuildValidationSnapshot CreateSnapshot(
        IReadOnlyDictionary<uint, int> materials) =>
        new(
            10, 20, 16, 10, 20, 313, 15, -1,
            0, 0, false, 1000, int.MaxValue, 15, materials);
}
