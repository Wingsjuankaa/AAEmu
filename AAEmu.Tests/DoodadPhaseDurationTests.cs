using System;

using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Mechanics;
using AAEmu.MechanicsLab;

using Xunit;

namespace AAEmu.Tests
{
    public class DoodadPhaseDurationTests
    {
        [Fact]
        public void CloutExposesItsNativeDurationToThePhasePacket()
        {
            var clout = new DoodadFuncClout { Duration = 7000 };

            Assert.Equal(7000, clout.GetPhaseDuration(new Doodad()));
        }

        [Fact]
        public void TimerExposesItsScheduledDurationToThePhasePacket()
        {
            var timer = new DoodadFuncTimer { Delay = 4999 };

            Assert.Equal(5000, timer.GetPhaseDuration(new Doodad()));
        }

        [Fact]
        public void TimeLeftUsesTheInstalledMechanicsClock()
        {
            var start = new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc);
            var clock = new ManualMechanicsClock(start);
            var doodad = new Doodad {GrowthTime = start.AddSeconds(7)};

            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                Assert.Equal((uint)7000, doodad.TimeLeft);
                clock.Advance(TimeSpan.FromMilliseconds(1250));
                Assert.Equal((uint)5750, doodad.TimeLeft);
            }
        }
    }
}
