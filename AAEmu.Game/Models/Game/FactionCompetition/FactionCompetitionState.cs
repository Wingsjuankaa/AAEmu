namespace AAEmu.Game.Models.Game.FactionCompetition;

/// <summary>
/// Deterministic, lock-free state machine. The manager owns synchronization and persistence.
/// Ranks are competition ranks: equal scores share a rank and the next rank is skipped.
/// </summary>
public sealed class FactionCompetitionState(FactionCompetitionTemplate template)
{
    private readonly Dictionary<int, uint> _points = [];

    public FactionCompetitionTemplate Template { get; } = template;
    public bool Active { get; private set; }
    public DateTime StartedAt { get; private set; }
    public DateTime EndsAt { get; private set; }
    public IReadOnlyDictionary<int, uint> Points => _points;

    public void Restore(bool active, DateTime startedAt, DateTime endsAt, IEnumerable<FactionCompetitionPoint> points)
    {
        Active = active;
        StartedAt = startedAt;
        EndsAt = endsAt;
        _points.Clear();
        foreach (var point in points)
            _points[point.FactionId] = point.Point;
    }

    public bool Start(DateTime startedAt, DateTime endsAt)
    {
        if (Active)
            return false;
        Active = true;
        StartedAt = startedAt;
        EndsAt = endsAt;
        return true;
    }

    public uint AddPoint(int factionId, uint amount)
    {
        if (!Active || factionId <= 0 || amount == 0)
            return GetPoint(factionId);
        var current = GetPoint(factionId);
        var next = current > uint.MaxValue - amount ? uint.MaxValue : current + amount;
        _points[factionId] = next;
        return next;
    }

    public uint GetPoint(int factionId) => _points.GetValueOrDefault(factionId);

    public IReadOnlyList<FactionCompetitionPoint> Snapshot() => _points
        .OrderBy(pair => pair.Key)
        .Select(pair => new FactionCompetitionPoint(pair.Key, pair.Value))
        .ToArray();

    public IReadOnlyDictionary<int, int> GetRanks()
    {
        var result = new Dictionary<int, int>();
        var ordered = _points.OrderByDescending(pair => pair.Value).ThenBy(pair => pair.Key).ToArray();
        uint? previousPoint = null;
        var rank = 0;
        for (var index = 0; index < ordered.Length; index++)
        {
            if (previousPoint != ordered[index].Value)
                rank = index + 1;
            result[ordered[index].Key] = rank;
            previousPoint = ordered[index].Value;
        }
        return result;
    }

    public int ResolveWinner()
    {
        if (_points.Count == 0)
            return 0;
        var ordered = _points.OrderByDescending(pair => pair.Value).ThenBy(pair => pair.Key).ToArray();
        if (ordered[0].Value < Template.RequiredPoint ||
            (ordered.Length > 1 && ordered[0].Value == ordered[1].Value))
            return 0;
        return ordered[0].Key;
    }

    public void FinishAndReset(int winnerFactionId)
    {
        Active = false;
        StartedAt = DateTime.MinValue;
        EndsAt = DateTime.MinValue;
        switch (Template.ResetKind)
        {
            case FactionCompetitionResetKind.WinnerOnly when winnerFactionId > 0:
                _points[winnerFactionId] = 0;
                break;
            case FactionCompetitionResetKind.All:
            case FactionCompetitionResetKind.AllIgnoreRequiredPoint:
                foreach (var factionId in _points.Keys.ToArray())
                    _points[factionId] = 0;
                break;
        }
    }
}
