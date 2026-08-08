using System;
using System.Threading.Tasks;

using AAEmu.Game.Models.Mechanics;

namespace AAEmu.MechanicsLab
{
    public sealed class ManualMechanicsClock : IMechanicsClock
    {
        public DateTime UtcNow { get; private set; }
        public event Action<DateTime> Advanced;

        public ManualMechanicsClock(DateTime utcNow)
        {
            UtcNow = utcNow.Kind == DateTimeKind.Utc ? utcNow : utcNow.ToUniversalTime();
        }

        public void Advance(TimeSpan amount)
        {
            if (amount < TimeSpan.Zero)
                throw new ArgumentOutOfRangeException(nameof(amount));
            UtcNow = UtcNow.Add(amount);
            Advanced?.Invoke(UtcNow);
        }

        public Task Delay(TimeSpan delay)
        {
            Advance(delay < TimeSpan.Zero ? TimeSpan.Zero : delay);
            return Task.CompletedTask;
        }
    }
}
