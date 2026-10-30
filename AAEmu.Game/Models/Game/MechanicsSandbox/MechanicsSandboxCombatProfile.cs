using AAEmu.Game.Models;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

/// <summary>
/// Explicit development build choice, not a claim that this retail system passive is NPC-only.
/// Keep its stored row intact so disabling this profile restores the original book on next load.
/// </summary>
internal static class MechanicsSandboxCombatProfile
{
    public const uint TreasureSystemPassiveId = 369;

    public static bool Excludes(MechanicsSandboxConfig config, uint characterId, uint accountId,
        string name, uint passiveId) => config is { Enabled: true, CombatProfile: true, CharacterId: > 0, AccountId: > 0 } &&
        characterId == config.CharacterId && accountId == config.AccountId &&
        string.Equals(name, config.CharacterName, StringComparison.Ordinal) &&
        passiveId == TreasureSystemPassiveId;
}
