using System.Collections.Generic;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;

using Xunit;

namespace AAEmu.Tests
{
    public class SorceryLiveTraceTests
    {
        [Fact]
        public void TraceAllowListMatchesTheExecutableV3Closure()
        {
            var expected = new HashSet<uint>
            {
                10151, 10153, 10664, 10667, 10670, 10752, 11314, 11939,
                11967, 12789, 12790, 12791, 12796, 14774, 15317, 23593,
                23646, 23647, 23648, 23649, 24894, 24895, 36474, 36475,
                36476, 36477, 36478, 36479, 37837, 39669, 39670, 39671,
                39672, 39673, 39674, 41222, 41223, 41478, 42012, 43068,
                43185, 43464, 43465
            };

            Assert.Equal(43, SorceryLiveTrace.TrackedSkillCount);
            foreach (var skillId in expected)
                Assert.True(SorceryLiveTrace.IsTrackedSkill(skillId), skillId.ToString());

            Assert.False(SorceryLiveTrace.IsTrackedSkill(2));
            Assert.False(SorceryLiveTrace.IsTrackedSkill(36480));
        }

        [Fact]
        public void StructuredEventIsStableAndMachineParseable()
        {
            var line = SorceryLiveTrace.FormatEvent(
                "effects_applied",
                10153,
                77,
                100,
                200,
                0,
                3,
                4567,
                20,
                2,
                4,
                SkillResult.Success,
                false);

            Assert.Equal(
                "[AA8SorceryLive] phase=effects_applied skill=10153 tlId=77 caster=100 target=200 world=0 instance=3 mp=4567 magicSource=20 targets=2 effects=4 result=Success cancelled=False",
                line);
        }
    }
}
