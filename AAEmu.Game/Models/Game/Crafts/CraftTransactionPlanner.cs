using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Crafts;

public enum CraftBlockReason
{
    None = 0,
    RecipeDisabled,
    InvalidRecipeShape,
    MissingSkill,
    MissingCraftEffect,
    MissingActabilityGroup,
    MaterialGradeDeferred,
    ProductGradeDeferred,
    ProductRateDeferred,
    BackpackDeferred,
    MissingMaterialTemplate,
    MissingProductTemplate,
    AmountOverflow
}

public enum CraftFailureCode
{
    None = 0,
    RecipeUnavailable,
    Busy,
    InvalidCount,
    UnsupportedRecipe,
    StationUnavailable,
    PermissionDenied,
    NotEnoughLabor,
    NotEnoughMoney,
    NotEnoughActability,
    MissingMaterials,
    ItemNotDestroyable,
    BagFull,
    BackpackOccupied,
    CannotChangeBackpackInGliding,
    ConcurrentChange,
    SkillRejected
}

public readonly record struct CraftFailure(
    CraftFailureCode Code,
    CraftBlockReason BlockReason = CraftBlockReason.None)
{
    public static CraftFailure None => new(CraftFailureCode.None);
    public static CraftFailure Blocked(CraftBlockReason reason) =>
        new(CraftFailureCode.UnsupportedRecipe, reason);
}

public sealed record CraftInventoryStack(uint ItemId, int Count, int Grade, bool CanDestroy);
public enum CraftBackpackSlotState
{
    Empty = 0,
    Glider,
    Occupied
}

public sealed record CraftInventorySnapshot(
    int FreeSlots,
    IReadOnlyList<CraftInventoryStack> Stacks,
    CraftBackpackSlotState BackpackSlot = CraftBackpackSlotState.Empty,
    bool IsGliding = false);
public sealed record CraftEconomySnapshot(long Money, int ActabilityPoints);

public sealed record CraftItemDefinition(
    uint ItemId,
    int MaxStackSize,
    int DefaultGrade,
    bool AutoEquipBackpack,
    ItemImplEnum ImplId = ItemImplEnum.Misc)
{
    public static CraftItemDefinition FromTemplate(ItemTemplate template, bool autoEquipBackpack)
    {
        if (template is null)
            return null;

        return new CraftItemDefinition(
            template.Id, template.MaxCount, Math.Max(0, template.FixedGrade),
            autoEquipBackpack, template.ImplId);
    }
}

/// <summary>
/// Exact material allocation for a committed transaction. Grade -1 is used only by the immutable
/// contract returned from TryValidateContract; plans returned by TryCreate contain concrete grades.
/// </summary>
public sealed record CraftMaterialRequirement(
    uint ItemId,
    int Amount,
    int Grade = -1,
    bool MainGrade = false);

public sealed record CraftProductGrant(
    uint ItemId,
    int Amount,
    int Grade,
    bool AutoEquipBackpack = false);

/// <summary>Immutable plan for one AA10 crafting step.</summary>
public sealed record CraftTransactionPlan(
    uint CraftId,
    int MoneyCost,
    int ActabilityLimit,
    uint ActabilityGroupId,
    bool IncludeActabilityBonuses,
    int CastDelay,
    IReadOnlyList<CraftMaterialRequirement> Materials,
    IReadOnlyList<CraftProductGrant> Products)
{
    /// <summary>AA10 product template ids whose probabilistic rate roll failed.</summary>
    public IReadOnlyList<int> FailedProductItemIds { get; init; } = [];

    /// <summary>
    /// True only when the runtime policy proved that this recipe intentionally consumes no items.
    /// </summary>
    public bool AllowsEmptyMaterials { get; init; }

    public CraftTransactionPlan(
        uint craftId,
        IReadOnlyList<CraftMaterialRequirement> materials,
        IReadOnlyList<CraftProductGrant> products)
        : this(craftId, 0, 0, 0, true, 0, materials, products)
    {
    }
}

/// <summary>
/// Pure AA10 Wave 3 planner. Grade selection is deterministic from the ordered inventory snapshot;
/// probabilistic outcomes are supplied as explicit rolls so tests and callers own all randomness.
/// </summary>
public static class CraftTransactionPlanner
{
    private static readonly HashSet<int> SupportedProductRates = [50, 100, 200];

    public static bool TryValidateContract(
        Craft craft,
        int count,
        Func<uint, CraftItemDefinition> itemResolver,
        bool hasCraftSkill,
        bool hasCraftEffect,
        uint actabilityGroupId,
        out CraftTransactionPlan plan,
        out CraftFailure failure)
    {
        plan = null;
        failure = CraftFailure.None;

        if (count <= 0)
            return Fail(CraftFailureCode.InvalidCount, out failure);
        if (craft is null || itemResolver is null)
            return Fail(CraftFailureCode.RecipeUnavailable, out failure);
        if (!craft.Enable)
            return Block(CraftBlockReason.RecipeDisabled, out failure);
        if (!hasCraftSkill)
            return Block(CraftBlockReason.MissingSkill, out failure);
        if (!hasCraftEffect)
            return Block(CraftBlockReason.MissingCraftEffect, out failure);
        if (craft.Cost < 0 || craft.ActabilityLimit < 0 || craft.CastDelay < 0)
            return Block(CraftBlockReason.InvalidRecipeShape, out failure);
        if ((craft.ActabilityLimit > 0 || craft.UseOnlyActability) && actabilityGroupId == 0)
            return Block(CraftBlockReason.MissingActabilityGroup, out failure);
        if ((!craft.AllowEmptyMaterials && craft.CraftMaterials.Count == 0) ||
            craft.CraftProducts.Count == 0)
            return Block(CraftBlockReason.InvalidRecipeShape, out failure);

        var materialTotals = new Dictionary<uint, int>();
        var materials = new List<CraftMaterialRequirement>(craft.CraftMaterials.Count);
        foreach (var material in craft.CraftMaterials)
        {
            if (material is null || material.ItemId == 0 || material.Amount <= 0 ||
                material.RequireGrade < -1 || material.RequireGrade > byte.MaxValue ||
                (material.UpperGrade && material.RequireGrade < 0))
                return Block(CraftBlockReason.InvalidRecipeShape, out failure);
            if (itemResolver(material.ItemId) is null)
                return Block(CraftBlockReason.MissingMaterialTemplate, out failure);
            if (!TryAdd(materialTotals, material.ItemId, material.Amount))
                return Block(CraftBlockReason.AmountOverflow, out failure);

            var contractGrade = material.RequireGrade >= 0 && !material.UpperGrade
                ? material.RequireGrade
                : -1;
            materials.Add(new CraftMaterialRequirement(
                material.ItemId, material.Amount, contractGrade, material.MainGrade));
        }

        var productTotals = new Dictionary<(uint ItemId, int Grade, bool AutoEquipBackpack), int>();
        foreach (var product in craft.CraftProducts)
        {
            if (product is null || product.ItemId == 0 || product.ItemId > int.MaxValue ||
                product.Amount <= 0 ||
                !SupportedProductRates.Contains(product.Rate) || product.ItemGradeId > byte.MaxValue)
                return Block(CraftBlockReason.InvalidRecipeShape, out failure);

            var definition = itemResolver(product.ItemId);
            if (definition is null || definition.MaxStackSize <= 0)
                return Block(CraftBlockReason.MissingProductTemplate, out failure);
            if (definition.AutoEquipBackpack && product.Amount != 1)
                return Block(CraftBlockReason.InvalidRecipeShape, out failure);

            var grade = product.UseGrade ? (int)product.ItemGradeId : definition.DefaultGrade;
            if (!TryAdd(
                    productTotals,
                    (product.ItemId, grade, definition.AutoEquipBackpack),
                    product.Amount))
                return Block(CraftBlockReason.AmountOverflow, out failure);
        }
        if (productTotals.Count(entry => entry.Key.AutoEquipBackpack) > 1)
            return Block(CraftBlockReason.InvalidRecipeShape, out failure);

        plan = new CraftTransactionPlan(
            craft.Id, craft.Cost, craft.ActabilityLimit, actabilityGroupId,
            !craft.UseOnlyActability, craft.CastDelay, materials,
            productTotals.Select(entry => new CraftProductGrant(
                entry.Key.ItemId, entry.Value, entry.Key.Grade,
                entry.Key.AutoEquipBackpack)).ToArray())
        {
            AllowsEmptyMaterials = craft.AllowEmptyMaterials
        };
        return true;
    }

    /// <summary>Plans a preflight in which every probabilistic product is assumed to succeed.</summary>
    public static bool TryCreate(
        Craft craft,
        int count,
        CraftInventorySnapshot inventory,
        CraftEconomySnapshot economy,
        Func<uint, CraftItemDefinition> itemResolver,
        bool hasCraftSkill,
        bool hasCraftEffect,
        uint actabilityGroupId,
        out CraftTransactionPlan plan,
        out CraftFailure failure) =>
        TryCreate(
            craft, count, inventory, economy, itemResolver, hasCraftSkill, hasCraftEffect,
            actabilityGroupId, null, out plan, out failure);

    /// <summary>
    /// Plans one final transaction. Rolls are values in [0,99], one per rate-50 product row;
    /// null means preflight and assumes success without consuming randomness.
    /// </summary>
    public static bool TryCreate(
        Craft craft,
        int count,
        CraftInventorySnapshot inventory,
        CraftEconomySnapshot economy,
        Func<uint, CraftItemDefinition> itemResolver,
        bool hasCraftSkill,
        bool hasCraftEffect,
        uint actabilityGroupId,
        IReadOnlyList<int> productRolls,
        out CraftTransactionPlan plan,
        out CraftFailure failure)
    {
        plan = null;
        failure = CraftFailure.None;

        if (inventory is null || economy is null)
            return Fail(CraftFailureCode.RecipeUnavailable, out failure);
        if (!TryValidateContract(
                craft, count, itemResolver, hasCraftSkill, hasCraftEffect, actabilityGroupId,
                out var contract, out failure))
            return false;
        if (economy.Money < contract.MoneyCost)
            return Fail(CraftFailureCode.NotEnoughMoney, out failure);
        if (economy.ActabilityPoints < contract.ActabilityLimit)
            return Fail(CraftFailureCode.NotEnoughActability, out failure);

        var remaining = inventory.Stacks
            .Select(stack => new MutableStack(
                stack.ItemId, stack.Count, stack.Grade, stack.CanDestroy))
            .ToList();
        var resolvedMaterials = new List<CraftMaterialRequirement>();
        var selectedMaterials = new List<SelectedMaterial>();

        foreach (var material in craft.CraftMaterials)
        {
            var needed = material.Amount;
            var lastGrade = -1;
            foreach (var stack in remaining.Where(entry =>
                         entry.ItemId == material.ItemId && entry.Count > 0 &&
                         GradeMatches(entry.Grade, material.RequireGrade, material.UpperGrade)))
            {
                var consumed = Math.Min(stack.Count, needed);
                if (consumed == stack.Count && !stack.CanDestroy)
                    return Fail(CraftFailureCode.ItemNotDestroyable, out failure);
                stack.Count -= consumed;
                needed -= consumed;
                lastGrade = stack.Grade;
                resolvedMaterials.Add(new CraftMaterialRequirement(
                    material.ItemId, consumed, stack.Grade, material.MainGrade));
                if (needed == 0)
                    break;
            }
            if (needed != 0)
                return Fail(CraftFailureCode.MissingMaterials, out failure);

            selectedMaterials.Add(new SelectedMaterial(
                lastGrade, material.MainGrade, itemResolver(material.ItemId).ImplId));
        }

        var productTotals = new Dictionary<(uint ItemId, int Grade, bool AutoEquipBackpack), int>();
        var failedProducts = new List<int>();
        var rollIndex = 0;
        foreach (var product in craft.CraftProducts)
        {
            var succeeds = true;
            if (product.Rate == 50 && productRolls is not null)
            {
                if (rollIndex >= productRolls.Count || productRolls[rollIndex] is < 0 or > 99)
                    return Fail(CraftFailureCode.ConcurrentChange, out failure);
                succeeds = productRolls[rollIndex++] < product.Rate;
            }

            if (!succeeds)
            {
                failedProducts.Add(checked((int)product.ItemId));
                continue;
            }

            var definition = itemResolver(product.ItemId);
            var grade = ResolveProductGrade(product, definition, selectedMaterials);
            if (!TryAdd(
                    productTotals,
                    (product.ItemId, grade, definition.AutoEquipBackpack),
                    product.Amount))
                return Block(CraftBlockReason.AmountOverflow, out failure);
        }
        if (productRolls is not null && rollIndex != productRolls.Count)
            return Fail(CraftFailureCode.ConcurrentChange, out failure);

        var products = productTotals.Select(entry => new CraftProductGrant(
            entry.Key.ItemId, entry.Value, entry.Key.Grade,
            entry.Key.AutoEquipBackpack)).ToArray();
        var freeSlots = inventory.FreeSlots + remaining.Count(entry => entry.Count == 0);
        var autoEquipProducts = products.Where(product => product.AutoEquipBackpack).ToArray();
        if (autoEquipProducts.Length > 1 || autoEquipProducts.Any(product => product.Amount != 1))
            return Fail(CraftFailureCode.ConcurrentChange, out failure);
        if (autoEquipProducts.Length == 1)
        {
            if (inventory.IsGliding)
                return Fail(CraftFailureCode.CannotChangeBackpackInGliding, out failure);
            if (inventory.BackpackSlot == CraftBackpackSlotState.Occupied)
                return Fail(CraftFailureCode.BackpackOccupied, out failure);
            if (inventory.BackpackSlot == CraftBackpackSlotState.Glider && --freeSlots < 0)
                return Fail(CraftFailureCode.BagFull, out failure);
        }

        foreach (var product in products.Where(product => !product.AutoEquipBackpack))
        {
            var definition = itemResolver(product.ItemId);
            var stackSpace = remaining
                .Where(entry => entry.Count > 0 && entry.ItemId == product.ItemId &&
                                entry.Grade == product.Grade)
                .Sum(entry => Math.Max(0L, (long)definition.MaxStackSize - entry.Count));
            var remainder = Math.Max(0L, (long)product.Amount - stackSpace);
            var requiredSlots = (remainder + definition.MaxStackSize - 1) / definition.MaxStackSize;
            if (requiredSlots > freeSlots)
                return Fail(CraftFailureCode.BagFull, out failure);
            freeSlots -= (int)requiredSlots;
        }

        var materialAllocations = resolvedMaterials
            .GroupBy(material => (material.ItemId, material.Grade, material.MainGrade))
            .Select(group => new CraftMaterialRequirement(
                group.Key.ItemId, group.Sum(material => material.Amount),
                group.Key.Grade, group.Key.MainGrade))
            .ToArray();

        plan = contract with
        {
            Materials = materialAllocations,
            Products = products,
            FailedProductItemIds = failedProducts
        };
        return true;
    }

    private static int ResolveProductGrade(
        CraftProduct product,
        CraftItemDefinition definition,
        IReadOnlyList<SelectedMaterial> selectedMaterials)
    {
        if (product.UseGrade)
            return (int)product.ItemGradeId;

        var main = selectedMaterials.FirstOrDefault(material => material.MainGrade);
        if (main is not null)
            return main.Grade;

        var grade = definition.DefaultGrade;
        foreach (var material in selectedMaterials)
            if (material.ImplId == definition.ImplId && material.Grade > grade)
                grade = material.Grade;
        return grade;
    }

    private static bool GradeMatches(int actualGrade, int requiredGrade, bool upperGrade) =>
        requiredGrade < 0 || (upperGrade ? actualGrade >= requiredGrade : actualGrade == requiredGrade);

    private static bool TryAdd<TKey>(IDictionary<TKey, int> values, TKey key, int amount)
    {
        try
        {
            values.TryGetValue(key, out var current);
            values[key] = checked(current + amount);
            return true;
        }
        catch (OverflowException)
        {
            return false;
        }
    }

    private static bool Block(CraftBlockReason reason, out CraftFailure failure)
    {
        failure = CraftFailure.Blocked(reason);
        return false;
    }

    private static bool Fail(CraftFailureCode code, out CraftFailure failure)
    {
        failure = new CraftFailure(code);
        return false;
    }

    private sealed record SelectedMaterial(int Grade, bool MainGrade, ItemImplEnum ImplId);

    private sealed class MutableStack(uint itemId, int count, int grade, bool canDestroy)
    {
        public uint ItemId { get; } = itemId;
        public int Count { get; set; } = count;
        public int Grade { get; } = grade;
        public bool CanDestroy { get; } = canDestroy;
    }
}
