namespace AAEmu.Game.Models.Game.Char;

/// <summary>Retains native buff notifications until the owning client finishes loading.</summary>
public sealed class PendingZoneBuffs
{
    private readonly object _lock = new();
    private readonly Queue<Action> _pending = new();
    private bool _ready;

    public void Receive(Action apply)
    {
        lock (_lock)
        {
            if (_ready)
                apply();
            else
                _pending.Enqueue(apply);
        }
    }

    public void CompleteLoading()
    {
        lock (_lock)
        {
            _ready = true;
            while (_pending.TryDequeue(out var apply))
                apply();
        }
    }

    public void Reset()
    {
        lock (_lock)
        {
            _ready = false;
            _pending.Clear();
        }
    }
}
