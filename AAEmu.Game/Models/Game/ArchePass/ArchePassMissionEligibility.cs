namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>Premium mission access follows the currently active pass, not previously owned upgrades.</summary>
public static class ArchePassMissionEligibility
{
    public static bool HasPremiumAccess(bool persistenceReady, CharacterArchePassState state,
        ArchePassTemplate template, DateTime utcNow) =>
        persistenceReady && state is { Status: ArchePassStatus.Progress, Premium: true } &&
        template is not null && template.Id == state.Type && template.IsAvailableAt(utcNow);
}
