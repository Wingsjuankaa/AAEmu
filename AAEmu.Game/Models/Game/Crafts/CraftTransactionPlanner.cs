using AAEmu.Game.Models.Game.Items.Templates;

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

public sealed record CraftInventoryStack(
    uint ItemId,
    int Count,
    int Grade,
    bool CanDestroy);

public sealed record CraftInventorySnapshot(
    int FreeSlots,
    IReadOnlyList<CraftInventoryStack> Stacks);

public sealed record CraftEconomySnapshot(
    long Money,
    int ActabilityPoints);

public sealed record CraftItemDefinition(
    uint ItemId,
    int MaxStackSize,
    int DefaultGrade,
    bool AutoEquipBackpack)
{
    public static CraftItemDefinition FromTemplate(ItemTemplate template, bool autoEquipBackpack)
    {
        if (template is null)
            return null;

        return new CraftItemDefinition(
            template.Id,
            template.MaxCount,
            Math.Max(0, template.FixedGrade),
            autoEquipBackpack);
    }
}

public sealed record CraftMaterialRequirement(uint ItemId, int Amount);
public sealed record CraftProductGrant(uint ItemId, int Amount, int Grade);

/// <summary>
/// Immutable plan for one AA10 crafting step.
/// </summary>
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
    public CraftTransactionPlan(
        uint craftId,
        IReadOnlyList<CraftMaterialRequirement> materials,
        IReadOnlyList<CraftProductGrant> products)
        : this(craftId, 0, 0, 0, true, 0, materials, products)
    {
    }
}

/// <summary>
/// Pure AA10 Wave 2 planner. Unsupported native shapes return a concrete block reason and never
/// delegate to the historical crafting path.
/// </summary>
public static class CraftTransactionPlanner
{
    /// <summary>
    /// Validates the immutable AA10 recipe contract without consulting mutable character state.
    /// This is intentionally separate from <see cref="TryCreate"/>: once the client submits a
    /// valid recipe it has already entered its batch-crafting state, so mutable failures must be
    /// reported from the skill lifecycle where SCSkillEnded can release that state.
    /// </summary>
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
        if (craft.CraftMaterials.Count == 0 || craft.CraftProducts.Count == 0)
            return Block(CraftBlockReason.InvalidRecipeShape, out failure);

        var materials = new SortedDictionary<uint, int>();
        foreach (var material in craft.CraftMaterials)
        {
            if (material is null || material.ItemId == 0 || material.Amount <= 0)
                return Block(CraftBlockReason.InvalidRecipeShape, out failure);
            if (material.RequireGrade != -1 || material.UpperGrade)
                return Block(CraftBlockReason.MaterialGradeDeferred, out failure);
            if (itemResolver(material.ItemId) is null)
                return Block(CraftBlockReason.MissingMaterialTemplate, out failure);
            if (!TryAdd(materials, material.ItemId, material.Amount))
                return Block(CraftBlockReason.AmountOverflow, out failure);
        }

        var products = new SortedDictionary<(uint ItemId, int Grade), int>();
        foreach (var product in craft.CraftProducts)
        {
            if (product is null || product.ItemId == 0 || product.Amount <= 0)
                return Block(CraftBlockReason.InvalidRecipeShape, out failure);
            if (product.Rate != 100)
                return Block(CraftBlockReason.ProductRateDeferred, out failure);
            if (product.UseGrade || product.ItemGradeId != 0)
                return Block(CraftBlockReason.ProductGradeDeferred, out failure);

            var definition = itemResolver(product.ItemId);
            if (definition is null || definition.MaxStackSize <= 0)
                return Block(CraftBlockReason.MissingProductTemplate, out failure);
            if (definition.AutoEquipBackpack)
                return Block(CraftBlockReason.BackpackDeferred, out failure);
            if (!TryAdd(products, (product.ItemId, definition.DefaultGrade), product.Amount))
                return Block(CraftBlockReason.AmountOverflow, out failure);
        }

        plan = new CraftTransactionPlan(
            craft.Id,
            craft.Cost,
            craft.ActabilityLimit,
            actabilityGroupId,
            !craft.UseOnlyActability,
            craft.CastDelay,
            materials.Select(entry => new CraftMaterialRequirement(entry.Key, entry.Value)).ToArray(),
            products.Select(entry => new CraftProductGrant(
                entry.Key.ItemId, entry.Value, entry.Key.Grade)).ToArray());
        return true;
    }

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
        foreach (var material in contract.Materials)
        {
            var itemId = material.ItemId;
            var requiredAmount = material.Amount;
            var needed = requiredAmount;
            foreach (var stack in remaining.Where(entry => entry.ItemId == itemId && entry.Count > 0))
            {
                var consumed = Math.Min(stack.Count, needed);
                if (consumed == stack.Count && !stack.CanDestroy)
                    return Fail(CraftFailureCode.ItemNotDestroyable, out failure);
                stack.Count -= consumed;
                needed -= consumed;
                if (needed == 0)
                    break;
            }
            if (needed != 0)
                return Fail(CraftFailureCode.MissingMaterials, out failure);
        }

        var freeSlots = inventory.FreeSlots + remaining.Count(entry => entry.Count == 0);
        foreach (var product in contract.Products)
        {
            var itemId = product.ItemId;
            var grade = product.Grade;
            var amount = product.Amount;
            var definition = itemResolver(itemId);
            var stackSpace = remaining
                .Where(entry => entry.Count > 0 && entry.ItemId == itemId && entry.Grade == grade)
                .Sum(entry => Math.Max(0L, (long)definition.MaxStackSize - entry.Count));
            var remainder = Math.Max(0L, (long)amount - stackSpace);
            var requiredSlots = (remainder + definition.MaxStackSize - 1) / definition.MaxStackSize;
            if (requiredSlots > freeSlots)
                return Fail(CraftFailureCode.BagFull, out failure);
            freeSlots -= (int)requiredSlots;
        }

        plan = contract;
        return true;
    }

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

    private sealed class MutableStack(uint itemId, int count, int grade, bool canDestroy)
    {
        public uint ItemId { get; } = itemId;
        public int Count { get; set; } = count;
        public int Grade { get; } = grade;
        public bool CanDestroy { get; } = canDestroy;
    }
}
