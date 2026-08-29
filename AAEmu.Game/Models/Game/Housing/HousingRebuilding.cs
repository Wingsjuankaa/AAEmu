namespace AAEmu.Game.Models.Game.Housing;

public enum HousingRebuildBlockReason
{
    None = 0,
    MissingPack,
    MissingTargetHousing,
    MissingMaterials,
    MissingItem,
    MissingSkillConsumer,
    TerritorialSubsystemRequired,
    SourceNotCompleted,
    NotOwner,
    ForSale,
    RouteDoesNotBelongToSource,
    SkillMismatch,
    DecorationsPresent,
    MissingLabor,
    MissingActability,
    MissingTaxPayment,
    MissingInteractionEvidence,
    ConcurrentChange
}

public sealed record HousingRebuildingMaterial(uint ItemId, int Count);

public sealed class HousingRebuildingDefinition
{
    public uint Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public uint SkillId { get; init; }
    public uint TargetHousingId { get; init; }
    public int LaborPower { get; init; }
    public uint ActabilityGroupId { get; init; }
    public string ChangePointDescription { get; init; } = string.Empty;
    public IReadOnlyList<HousingRebuildingMaterial> Materials { get; internal set; } = [];
    public HousingTemplate TargetTemplate { get; internal set; }
    public HousingRebuildBlockReason BlockReason { get; internal set; }

    public bool IsExecutable => BlockReason == HousingRebuildBlockReason.None;
}

public sealed record HousingRebuildingRoute(
    uint PackId,
    int Position,
    HousingRebuildingDefinition Definition);

public static class HousingRebuildingRouteSelector
{
    public static HousingRebuildingRoute FindByTargetHousingId(
        IReadOnlyList<HousingRebuildingRoute> routes,
        uint targetHousingId)
    {
        if (routes is null || targetHousingId == 0)
            return null;

        return routes.FirstOrDefault(route =>
            route?.Definition?.TargetHousingId == targetHousingId);
    }
}

public sealed record HousingRebuildFailure(HousingRebuildBlockReason Reason)
{
    public static HousingRebuildFailure None { get; } = new(HousingRebuildBlockReason.None);
}

/// <summary>
/// Immutable inputs captured by the executor while holding the housing lock. This keeps planning
/// deterministic and independently testable; no Character, House or inventory object is retained.
/// </summary>
public sealed record HousingRebuildValidationSnapshot(
    uint CharacterId,
    uint CharacterAccountId,
    uint HouseId,
    uint HouseOwnerId,
    uint HouseAccountId,
    uint SourceHousingId,
    uint SourcePackId,
    int CurrentStep,
    uint SellPrice,
    uint SellToPlayerId,
    bool HasDecorations,
    int AvailableLabor,
    int AvailableActability,
    int AvailableTaxCertificates,
    IReadOnlyDictionary<uint, int> AvailableMaterials);

/// <summary>
/// Immutable result of validating one AA10 housing-rebuild request. The mutable House and Character
/// are deliberately not retained: the executor must revalidate under the housing transaction lock.
/// </summary>
public sealed record HousingRebuildTransactionPlan(
    uint HouseId,
    uint SourceHousingId,
    uint TargetHousingId,
    uint RebuildingId,
    uint SkillId,
    int LaborPower,
    uint ActabilityGroupId,
    int TaxCertificateCost,
    IReadOnlyList<HousingRebuildingMaterial> Materials);

public static class HousingRebuildTransactionPlanner
{
    public static bool TryCreate(
        HousingRebuildValidationSnapshot snapshot,
        HousingRebuildingRoute route,
        uint usedSkillId,
        int taxCertificateCost,
        out HousingRebuildTransactionPlan plan,
        out HousingRebuildFailure failure)
    {
        plan = null;
        failure = HousingRebuildFailure.None;

        var definition = route?.Definition;
        if (snapshot is null || definition is null || !definition.IsExecutable)
            return Fail(definition?.BlockReason ?? HousingRebuildBlockReason.ConcurrentChange, out failure);
        if (snapshot.CurrentStep != -1)
            return Fail(HousingRebuildBlockReason.SourceNotCompleted, out failure);
        if (snapshot.HouseOwnerId != snapshot.CharacterId ||
            snapshot.HouseAccountId != snapshot.CharacterAccountId)
            return Fail(HousingRebuildBlockReason.NotOwner, out failure);
        if (snapshot.SellPrice != 0 || snapshot.SellToPlayerId != 0)
            return Fail(HousingRebuildBlockReason.ForSale, out failure);
        if (snapshot.SourcePackId != route.PackId)
            return Fail(HousingRebuildBlockReason.RouteDoesNotBelongToSource, out failure);
        if (usedSkillId == 0 || usedSkillId != definition.SkillId)
            return Fail(HousingRebuildBlockReason.SkillMismatch, out failure);
        if (snapshot.HasDecorations)
            return Fail(HousingRebuildBlockReason.DecorationsPresent, out failure);
        if (definition.LaborPower < 0 || snapshot.AvailableLabor < definition.LaborPower)
            return Fail(HousingRebuildBlockReason.MissingLabor, out failure);
        if (definition.ActabilityGroupId > 0 &&
            snapshot.AvailableActability < definition.LaborPower)
            return Fail(HousingRebuildBlockReason.MissingActability, out failure);
        if (taxCertificateCost < 0 || snapshot.AvailableTaxCertificates < taxCertificateCost)
            return Fail(HousingRebuildBlockReason.MissingTaxPayment, out failure);

        foreach (var requirement in definition.Materials
                     .GroupBy(material => material.ItemId)
                     .Select(group => new HousingRebuildingMaterial(
                         group.Key, group.Sum(material => material.Count))))
            if (requirement.ItemId == 0 || requirement.Count <= 0 ||
                !snapshot.AvailableMaterials.TryGetValue(requirement.ItemId, out var available) ||
                available < requirement.Count)
                return Fail(HousingRebuildBlockReason.MissingMaterials, out failure);

        plan = new HousingRebuildTransactionPlan(
            snapshot.HouseId,
            snapshot.SourceHousingId,
            definition.TargetHousingId,
            definition.Id,
            definition.SkillId,
            definition.LaborPower,
            definition.ActabilityGroupId,
            taxCertificateCost,
            definition.Materials);
        return true;
    }

    private static bool Fail(HousingRebuildBlockReason reason, out HousingRebuildFailure failure)
    {
        failure = new HousingRebuildFailure(reason);
        return false;
    }
}
