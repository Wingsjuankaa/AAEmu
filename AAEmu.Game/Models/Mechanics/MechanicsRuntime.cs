using System;
using System.Collections.Generic;
using System.Net;
using System.Threading;
using System.Threading.Tasks;

using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

using GameTask = AAEmu.Game.Models.Tasks.Task;

namespace AAEmu.Game.Models.Mechanics
{
    /// <summary>
    /// Narrow, process-local seams used by the headless mechanics laboratory.
    /// Production code sees a null Current context and keeps the original
    /// Quartz, wall-clock, world, loot and socket implementations.
    /// </summary>
    public sealed class MechanicsRuntimeContext
    {
        public IMechanicsClock Clock { get; set; }
        public IMechanicsScheduler Scheduler { get; set; }
        public IMechanicsWorld World { get; set; }
        public IMechanicsPacketObserver PacketObserver { get; set; }
        public IMechanicsDeathSink DeathSink { get; set; }
        public IMechanicsExceptionSink ExceptionSink { get; set; }
        public IMechanicsEventSink EventSink { get; set; }
        public bool SuppressLoot { get; set; }
        public bool SuppressNpcAi { get; set; }
        public bool ContinueProductionDeathClosure { get; set; }
        public double ExperienceRate { get; set; } = 1d;
        public Func<Func<Task>, Task> BackgroundRunner { get; set; }
    }

    public interface IMechanicsClock
    {
        DateTime UtcNow { get; }
        Task Delay(TimeSpan delay);
    }

    public interface IMechanicsScheduler
    {
        void Schedule(GameTask task, TimeSpan? startTime, TimeSpan? repeatInterval, int count);
        Task<bool> Cancel(GameTask task);
        int PendingCount { get; }
    }

    public interface IMechanicsWorld
    {
        GameObject GetGameObject(uint objId);
        BaseUnit GetBaseUnit(uint objId);
        Unit GetUnit(uint objId);
        IReadOnlyList<GameObject> GetAround(GameObject origin, float? radius, bool useModelSize);
    }

    public interface IMechanicsPacketObserver
    {
        void RecordPlaintext(GamePacket packet, byte counter, byte[] plaintext);
        void RecordWire(GamePacket packet, byte[] wire);
    }

    public interface IMechanicsPacketTransport
    {
        uint SessionId { get; }
        IPAddress Ip { get; }
        bool Send(byte[] wire);
    }

    public interface IMechanicsDeathSink
    {
        void RecordNpcDeath(Npc npc, Unit killer);
    }

    public interface IMechanicsExceptionSink
    {
        void RecordException(string boundary, Exception exception);
    }

    public interface IMechanicsEventSink
    {
        void RecordEvent(string eventName, uint actorId, uint targetId, string detail);
    }

    public static class MechanicsRuntime
    {
        private static readonly AsyncLocal<MechanicsRuntimeContext> Active =
            new AsyncLocal<MechanicsRuntimeContext>();

        public static MechanicsRuntimeContext Current => Active.Value;

        public static DateTime UtcNow => Current?.Clock?.UtcNow ?? DateTime.UtcNow;

        public static IDisposable Push(MechanicsRuntimeContext context)
        {
            if (context == null)
                throw new ArgumentNullException(nameof(context));

            var previous = Active.Value;
            Active.Value = context;
            return new RestoreScope(() => Active.Value = previous);
        }

        public static Task Delay(TimeSpan delay)
        {
            return Current?.Clock?.Delay(delay) ?? Task.Delay(delay);
        }

        public static void RunBackground(Func<Task> action)
        {
            if (action == null)
                return;

            var context = Current;
            if (context == null)
            {
                _ = Task.Run(action);
                return;
            }

            if (context.BackgroundRunner != null)
                context.BackgroundRunner(action).GetAwaiter().GetResult();
            else
                action().GetAwaiter().GetResult();
        }

        private sealed class RestoreScope : IDisposable
        {
            private Action _restore;

            public RestoreScope(Action restore)
            {
                _restore = restore;
            }

            public void Dispose()
            {
                Interlocked.Exchange(ref _restore, null)?.Invoke();
            }
        }
    }
}
