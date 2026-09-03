namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>
/// Retail r575 registration invariants. The client considers a book full after six
/// passes in <see cref="ArchePassStatus.Owned"/> or <see cref="ArchePassStatus.Progress"/>
/// state, while at most one registered pass may be in progress.
/// </summary>
public static class ArchePassRegistrationPolicy
{
    public const int Capacity = 6;

    public static bool IsRegistered(ArchePassStatus status) =>
        status is ArchePassStatus.Owned or ArchePassStatus.Progress;

    public static bool IsFull(IEnumerable<ArchePassStatus> statuses) =>
        statuses.Count(IsRegistered) >= Capacity;

    public static bool HasValidPersistenceState(IEnumerable<ArchePassStatus> statuses)
    {
        var materialized = statuses as IReadOnlyCollection<ArchePassStatus> ?? statuses.ToArray();
        return materialized.Count(IsRegistered) <= Capacity &&
               materialized.Count(status => status == ArchePassStatus.Progress) <= 1;
    }

    /// <summary>
    /// Starts an owned pass while preserving the retail single-active invariant. If another pass
    /// is active, it is paused back to <see cref="ArchePassStatus.Owned"/> without losing its
    /// points, premium state or claimed reward frontiers.
    /// </summary>
    public static bool TryActivate(
        IReadOnlyDictionary<int, CharacterArchePassState> states,
        int targetType,
        out CharacterArchePassState paused,
        out CharacterArchePassState started)
    {
        paused = null;
        started = null;
        if (!states.TryGetValue(targetType, out var target) || target.Status != ArchePassStatus.Owned)
            return false;

        var activeStates = states.Values
            .Where(state => state.Status == ArchePassStatus.Progress)
            .Take(2)
            .ToArray();
        if (activeStates.Length > 1)
            return false;

        paused = activeStates.SingleOrDefault();
        if (paused is not null)
            paused.Status = ArchePassStatus.Owned;

        target.Status = ArchePassStatus.Progress;
        started = target;
        return true;
    }
}
