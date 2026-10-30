using System.Runtime.CompilerServices;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

/// <summary>
/// Development-only reset fence. Ordinary actors have no registration and take the no-op path.
/// A scheduled callback captures an epoch; resetting retires that epoch permanently, including
/// callbacks holding a reusable Skill whose Cancelled/TlId fields later belong to another cast.
/// </summary>
public static class MechanicsSandboxExecution
{
    private static readonly ConditionalWeakTable<object, Scope> s_actors = new();
    private static readonly object s_registryGate = new();

    public readonly record struct Stamp(Scope Owner, long Generation);

    public sealed class Lease : IDisposable
    {
        private readonly object _gate;
        public bool Allowed { get; }
        public Stamp Stamp { get; }
        internal Lease(bool allowed, Stamp stamp = default, object gate = null)
        {
            Allowed = allowed;
            Stamp = stamp;
            _gate = gate;
        }
        public void Dispose()
        {
            if (_gate != null)
                Monitor.Exit(_gate);
        }
    }

    public sealed class Scope : IDisposable
    {
        internal object Gate { get; } = new();
        internal long Generation { get; private set; } = 1;
        internal bool Resetting { get; private set; }
        internal bool Retired { get; private set; }
        private int _mutationThread;
        internal bool IsMutationThread => _mutationThread == Environment.CurrentManagedThreadId;
        private readonly List<object> _actors = [];
        private readonly Dictionary<Skill, Unit> _skills = new(ReferenceEqualityComparer.Instance);

        public void AddActor(object actor)
        {
            ArgumentNullException.ThrowIfNull(actor);
            lock (Gate)
            lock (s_registryGate)
            {
                if (Retired)
                    throw new InvalidOperationException("El escenario ya se cerró.");
                if (s_actors.TryGetValue(actor, out var owner))
                {
                    if (ReferenceEquals(owner, this))
                        return;
                    throw new InvalidOperationException("El actor ya pertenece a otro escenario.");
                }
                s_actors.Add(actor, this);
                _actors.Add(actor);
            }
        }

        public void RemoveActor(object actor)
        {
            lock (Gate)
            lock (s_registryGate)
            {
                if (s_actors.TryGetValue(actor, out var owner) && ReferenceEquals(owner, this))
                    s_actors.Remove(actor);
                _actors.Remove(actor);
            }
        }

        public void Track(Skill skill, Unit caster)
        {
            lock (Gate)
            {
                // Retain active overlapping/background plots, not an unbounded history of finished casts.
                foreach (var finished in _skills.Keys.Where(s => s.TlId == 0 && s.ActivePlotState == null).ToArray())
                    _skills.Remove(finished);
                _skills[skill] = caster;
            }
        }

        public IReadOnlyList<(Skill Skill, Unit Caster)> BeginReset()
        {
            lock (Gate)
            {
                // An explicit retry after a failed restore must retire its partially created epoch too.
                Resetting = true;
                Generation++;
                return _skills.Select(pair => (pair.Key, pair.Value)).ToArray();
            }
        }

        public void CompleteReset()
        {
            lock (Gate)
            {
                foreach (var old in _skills.Keys.Where(skill =>
                             !ReferenceEquals(skill.SandboxExecutionStamp.Owner, this) ||
                             skill.SandboxExecutionStamp.Generation != Generation).ToArray())
                    _skills.Remove(old);
                Resetting = false;
            }
        }

        public void Mutate(Action restore)
        {
            lock (Gate)
            {
                var previous = _mutationThread;
                _mutationThread = Environment.CurrentManagedThreadId;
                try { restore(); }
                finally { _mutationThread = previous; }
            }
        }

        public void Dispose()
        {
            lock (Gate)
            {
                Retired = true;
                Resetting = true;
                Generation++;
                foreach (var actor in _actors.ToArray())
                    RemoveActor(actor);
                _skills.Clear();
            }
        }
    }

    public static Stamp Capture(object actor)
    {
        if (actor == null || !s_actors.TryGetValue(actor, out var scope))
            return default;
        lock (scope.Gate)
            return new Stamp(scope, scope.Generation);
    }

    public static Lease EnterCurrent(object actor)
    {
        if (actor == null || !s_actors.TryGetValue(actor, out var scope))
            return new Lease(true);
        Monitor.Enter(scope.Gate);
        var registered = s_actors.TryGetValue(actor, out var current) && ReferenceEquals(current, scope);
        return new Lease(registered && !scope.Retired && (!scope.Resetting || scope.IsMutationThread), new Stamp(scope, scope.Generation), scope.Gate);
    }

    public static Lease EnterScheduled(object actor, Stamp stamp)
    {
        var current = actor != null && s_actors.TryGetValue(actor, out var value) ? value : null;
        if (stamp.Owner == null)
            return new Lease(current == null);
        var scope = stamp.Owner;
        Monitor.Enter(scope.Gate);
        current = actor != null && s_actors.TryGetValue(actor, out value) ? value : null;
        return new Lease(ReferenceEquals(current, scope) && !scope.Retired && (!scope.Resetting || scope.IsMutationThread) &&
                         scope.Generation == stamp.Generation, stamp, scope.Gate);
    }
}
