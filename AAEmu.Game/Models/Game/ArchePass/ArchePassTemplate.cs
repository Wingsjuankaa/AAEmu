namespace AAEmu.Game.Models.Game.ArchePass;

public sealed class ArchePassTemplate
{
    public int Id { get; init; }
    public uint CategoryId { get; init; }
    public bool CategoryEnabled { get; init; }
    public DateTime? EndAtUtc { get; init; }
    public uint CurrencyId { get; init; }
    public long CurrencyValue { get; init; }
    public uint UpgradeItemId { get; init; }
    public int MaxTier { get; init; }
    public IReadOnlyList<ArchePassTierTemplate> Tiers { get; internal set; } = [];

    public bool HasCompleteTierCatalog =>
        MaxTier > 0 && Tiers.Count == MaxTier &&
        Tiers[0].Tier == 1 && Tiers[^1].Tier == MaxTier &&
        Tiers.Select(tier => tier.Tier).Distinct().Count() == MaxTier;

    public bool IsAvailableAt(DateTime utcNow) =>
        CategoryEnabled && HasCompleteTierCatalog &&
        (EndAtUtc is null || utcNow < EndAtUtc.Value);
}

public sealed record ArchePassTierTemplate(
    int Tier,
    long Point,
    uint RewardItemId,
    int RewardItemCount,
    uint PremiumRewardItemId,
    int PremiumRewardItemCount);
