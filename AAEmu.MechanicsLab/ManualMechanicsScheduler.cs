using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using AAEmu.Game.Models.Mechanics;

using GameTask = AAEmu.Game.Models.Tasks.Task;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsTaskEvent
    {
        public long Sequence { get; set; }
        public DateTime TimestampUtc { get; set; }
        public string Event { get; set; }
        public string Task { get; set; }
        public uint TaskId { get; set; }
        public string Exception { get; set; }
    }

    public sealed class ManualMechanicsScheduler : IMechanicsScheduler
    {
        private readonly ManualMechanicsClock _clock;
        private readonly List<ScheduledEntry> _entries = new List<ScheduledEntry>();
        private uint _nextId = 1;
        private long _sequence;
        private bool _running;

        public List<MechanicsTaskEvent> Timeline { get; } = new List<MechanicsTaskEvent>();
        public List<Exception> Exceptions { get; } = new List<Exception>();
        public int PendingCount => _entries.Count(entry => !entry.Task.Cancelled);

        public ManualMechanicsScheduler(ManualMechanicsClock clock)
        {
            _clock = clock;
            _clock.Advanced += _ => RunDue();
        }

        public void Schedule(GameTask task, TimeSpan? startTime, TimeSpan? repeatInterval, int count)
        {
            if (task == null)
                throw new ArgumentNullException(nameof(task));
            task.Id = _nextId++;
            task.ScheduleTime = new DateTimeOffset(_clock.UtcNow).ToUnixTimeMilliseconds();
            task.MaxCount = repeatInterval == null ? 0 : count;
            task.ExecuteCount = 0;
            _entries.Add(new ScheduledEntry
            {
                Task = task,
                DueUtc = _clock.UtcNow.Add(startTime ?? TimeSpan.Zero),
                Repeat = repeatInterval,
                RemainingRepeats = count
            });
            Record("scheduled", task, null);
            RunDue();
        }

        public Task<bool> Cancel(GameTask task)
        {
            var entry = _entries.FirstOrDefault(candidate => ReferenceEquals(candidate.Task, task));
            if (entry == null)
                return Task.FromResult(true);
            task.Cancelled = true;
            _entries.Remove(entry);
            Record("cancelled", task, null);
            return Task.FromResult(true);
        }

        public void RunDue()
        {
            if (_running)
                return;
            _running = true;
            try
            {
                while (true)
                {
                    var entry = _entries
                        .Where(candidate => !candidate.Task.Cancelled && candidate.DueUtc <= _clock.UtcNow)
                        .OrderBy(candidate => candidate.DueUtc)
                        .ThenBy(candidate => candidate.Task.Id)
                        .FirstOrDefault();
                    if (entry == null)
                        break;

                    try
                    {
                        Record("executing", entry.Task, null);
                        entry.Task.Execute();
                        entry.Task.ExecuteCount++;
                        Record("executed", entry.Task, null);
                    }
                    catch (Exception exception)
                    {
                        Exceptions.Add(exception);
                        Record("exception", entry.Task, exception);
                    }

                    if (entry.Repeat == null || entry.Task.Cancelled || entry.RemainingRepeats == 0)
                    {
                        _entries.Remove(entry);
                        continue;
                    }

                    if (entry.RemainingRepeats > 0)
                        entry.RemainingRepeats--;
                    entry.DueUtc = entry.DueUtc.Add(entry.Repeat.Value);
                }
            }
            finally
            {
                _running = false;
            }
        }

        private void Record(string eventName, GameTask task, Exception exception)
        {
            Timeline.Add(new MechanicsTaskEvent
            {
                Sequence = ++_sequence,
                TimestampUtc = _clock.UtcNow,
                Event = eventName,
                Task = task?.GetType().FullName,
                TaskId = task?.Id ?? 0,
                Exception = exception?.ToString()
            });
        }

        private sealed class ScheduledEntry
        {
            public GameTask Task { get; set; }
            public DateTime DueUtc { get; set; }
            public TimeSpan? Repeat { get; set; }
            public int RemainingRepeats { get; set; }
        }
    }
}
