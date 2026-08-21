namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>Pure AA10 tier/claim rules shared by runtime validation and unit fixtures.</summary>
public static class ArchePassProgression
{
    public static int GetCurrentTier(ArchePassTemplate template, long point)
    {
        if (template is null || template.Tiers.Count == 0 || point < 0)
            return 0;

        var current = 0;
        foreach (var tier in template.Tiers)
        {
            if (tier.Point > point)
                break;
            current = tier.Tier;
        }
        return current;
    }

    public static long AddPoints(ArchePassTemplate template, long current, int amount)
    {
        if (template is null || !template.HasCompleteTierCatalog || current < 0 || amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount));

        var cap = template.Tiers[^1].Point;
        if (current >= cap || amount == 0)
            return Math.Min(current, cap);
        return Math.Min(checked(current + amount), cap);
    }

    public static int GetNextClaimableTier(
        ArchePassTemplate template,
        CharacterArchePassState state,
        bool premium,
        bool requireReached)
    {
        if (template is null || state is null)
            return 0;

        var last = premium ? state.LastPremiumRewardTier : state.LastRewardTier;
        foreach (var tier in template.Tiers)
        {
            if (tier.Tier <= last)
                continue;
            if (requireReached && tier.Point > state.Point)
                return 0;

            var itemId = premium ? tier.PremiumRewardItemId : tier.RewardItemId;
            var itemCount = premium ? tier.PremiumRewardItemCount : tier.RewardItemCount;
            if (itemId != 0 && itemCount > 0)
                return tier.Tier;
        }
        return 0;
    }

    public static bool CanCompleteNormal(ArchePassTemplate template, CharacterArchePassState state) =>
        template is not null && state is not null && !state.Premium &&
        GetCurrentTier(template, state.Point) == template.MaxTier &&
        GetNextClaimableTier(template, state, false, false) == 0;

    public static bool CanCompletePremium(ArchePassTemplate template, CharacterArchePassState state) =>
        template is not null && state is not null && state.Premium &&
        GetCurrentTier(template, state.Point) == template.MaxTier &&
        GetNextClaimableTier(template, state, false, false) == 0 &&
        GetNextClaimableTier(template, state, true, false) == 0;
}
