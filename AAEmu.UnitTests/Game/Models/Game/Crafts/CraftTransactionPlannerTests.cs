using AAEmu.Game.Models.Game.Crafts;

namespace AAEmu.UnitTests.Game.Models.Game.Crafts;

public class CraftTransactionPlannerTests
{
    private static readonly IReadOnlyDictionary<uint, CraftItemDefinition> Definitions =
        new Dictionary<uint, CraftItemDefinition>
        {
            [10] = new(10, 100, 0, false),
            [11] = new(11, 100, 0, false),
            [20] = new(20, 10, 0, false),
            [21] = new(21, 1, 0, false),
            [22] = new(22, 1, 0, true)
        };

    [Test]
    public async Task AggregatesDuplicateRowsAndPlansOneStep()
    {
        var craft = CreateCraft();
        craft.CraftMaterials.Add(new CraftMaterial { ItemId = 10, Amount = 3, RequireGrade = -1 });
        craft.CraftProducts.Add(new CraftProduct { ItemId = 21, Amount = 2, Rate = 100 });

        var ok = TryPlan(craft, 1, new CraftInventorySnapshot(3,
            [new CraftInventoryStack(10, 5, 0, true)]), out var plan, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
        await Assert.That(plan.Materials.Count).IsEqualTo(1);
        await Assert.That(plan.Materials[0]).IsEqualTo(new CraftMaterialRequirement(10, 5));
        await Assert.That(plan.Products.Count).IsEqualTo(1);
        await Assert.That(plan.Products[0]).IsEqualTo(new CraftProductGrant(21, 3, 0));
    }

    [Test]
    public async Task CapacityUsesSlotReleasedByConsumption()
    {
        var craft = CreateCraft();
        var ok = TryPlan(craft, 1, new CraftInventorySnapshot(0,
            [new CraftInventoryStack(10, 2, 0, true)]), out _, out var failure);

        await Assert.That(ok).IsTrue();
        await Assert.That(failure).IsEqualTo(CraftFailure.None);
    }

    [Test]
    public async Task MissingMaterialAndNonDestroyableStackFailWithoutPlan()
    {
        var craft = CreateCraft();
        var missing = TryPlan(craft, 1, new CraftInventorySnapshot(2, []), out var missingPlan,
            out var missingFailure);
        var locked = TryPlan(craft, 1, new CraftInventorySnapshot(2,
            [new CraftInventoryStack(10, 2, 0, false)]), out var lockedPlan, out var lockedFailure);

        await Assert.That(missing).IsFalse();
        await Assert.That(missingPlan).IsNull();
        await Assert.That(missingFailure.Code).IsEqualTo(CraftFailureCode.MissingMaterials);
        await Assert.That(locked).IsFalse();
        await Assert.That(lockedPlan).IsNull();
        await Assert.That(lockedFailure.Code).IsEqualTo(CraftFailureCode.ItemNotDestroyable);
    }

    [Test]
    public async Task FullBagFailsWhenConsumptionDoesNotReleaseCapacity()
    {
        var craft = CreateCraft();
        var ok = TryPlan(craft, 1, new CraftInventorySnapshot(0,
        [
            new CraftInventoryStack(10, 3, 0, true),
            new CraftInventoryStack(11, 1, 0, true)
        ]), out _, out var failure);

        await Assert.That(ok).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.BagFull);
    }

    [Test]
    public async Task ValidContractRemainsSeparateFromMutableInventoryFailure()
    {
        var craft = CreateCraft();

        var contractOk = CraftTransactionPlanner.TryValidateContract(
            craft, 1, id => Definitions.GetValueOrDefault(id), true, true,
            out var contract, out var contractFailure);
        var transactionOk = TryPlan(
            craft, 1, new CraftInventorySnapshot(0, []), out var transaction,
            out var transactionFailure);

        await Assert.That(contractOk).IsTrue();
        await Assert.That(contractFailure).IsEqualTo(CraftFailure.None);
        await Assert.That(contract).IsNotNull();
        await Assert.That(transactionOk).IsFalse();
        await Assert.That(transaction).IsNull();
        await Assert.That(transactionFailure.Code).IsEqualTo(CraftFailureCode.MissingMaterials);
    }

    [Test]
    public async Task WaveOneRejectsRepeatCostGradeRateActabilityAndBackpackContracts()
    {
        var inventory = new CraftInventorySnapshot(2, [new CraftInventoryStack(10, 20, 0, true)]);

        var repeat = CreateCraft();
        TryPlan(repeat, 2, inventory, out _, out var repeatFailure);

        var paid = CreateCraft();
        paid.Cost = 1;
        TryPlan(paid, 1, inventory, out _, out var paidFailure);

        var materialGrade = CreateCraft();
        materialGrade.CraftMaterials[0].RequireGrade = 0;
        TryPlan(materialGrade, 1, inventory, out _, out var materialGradeFailure);

        var rate = CreateCraft();
        rate.CraftProducts[0].Rate = 50;
        TryPlan(rate, 1, inventory, out _, out var rateFailure);

        var actability = CreateCraft();
        actability.ActabilityLimit = 1;
        TryPlan(actability, 1, inventory, out _, out var actabilityFailure);

        var backpack = CreateCraft();
        backpack.CraftProducts[0].ItemId = 22;
        TryPlan(backpack, 1, inventory, out _, out var backpackFailure);

        await Assert.That(repeatFailure.Code).IsEqualTo(CraftFailureCode.InvalidCount);
        await Assert.That(paidFailure.BlockReason).IsEqualTo(CraftBlockReason.CostDeferred);
        await Assert.That(materialGradeFailure.BlockReason).IsEqualTo(CraftBlockReason.MaterialGradeDeferred);
        await Assert.That(rateFailure.BlockReason).IsEqualTo(CraftBlockReason.ProductRateDeferred);
        await Assert.That(actabilityFailure.BlockReason).IsEqualTo(CraftBlockReason.ActabilityDeferred);
        await Assert.That(backpackFailure.BlockReason).IsEqualTo(CraftBlockReason.BackpackDeferred);
    }

    [Test]
    public async Task CheckedAggregationRejectsOverflow()
    {
        var craft = CreateCraft();
        craft.CraftMaterials[0].Amount = int.MaxValue;
        craft.CraftMaterials.Add(new CraftMaterial { ItemId = 10, Amount = 1, RequireGrade = -1 });

        TryPlan(craft, 1, new CraftInventorySnapshot(1,
            [new CraftInventoryStack(10, int.MaxValue, 0, true)]), out var plan, out var failure);

        await Assert.That(plan).IsNull();
        await Assert.That(failure.BlockReason).IsEqualTo(CraftBlockReason.AmountOverflow);
    }

    private static Craft CreateCraft() => new()
    {
        Id = 1,
        Enable = true,
        SkillId = 100,
        CraftMaterials = [new CraftMaterial { ItemId = 10, Amount = 2, RequireGrade = -1 }],
        CraftProducts = [new CraftProduct { ItemId = 21, Amount = 1, Rate = 100 }]
    };

    private static bool TryPlan(
        Craft craft,
        int count,
        CraftInventorySnapshot inventory,
        out CraftTransactionPlan plan,
        out CraftFailure failure) =>
        CraftTransactionPlanner.TryCreate(
            craft, count, inventory, id => Definitions.GetValueOrDefault(id), true, true,
            out plan, out failure);
}
