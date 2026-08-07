using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;

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
    }
}
