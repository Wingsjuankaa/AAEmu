namespace AAEmu.Game.Models.Game.Trading;

/// <summary>
/// One inclusive age boundary from <c>freshness_group_items</c>.
/// Reward rates use 1000 as neutral; seller-share values use ten percent per unit.
/// </summary>
public sealed class FreshnessGroupItem
{
    public uint Id { get; set; }
    public uint FreshnessGroupId { get; set; }
    public uint Time { get; set; }
    public int RewardRate { get; set; }
    public int SellerShareRatio { get; set; }
}
