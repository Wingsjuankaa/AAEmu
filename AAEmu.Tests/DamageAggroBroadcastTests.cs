using System.Reflection;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;

using Xunit;

namespace AAEmu.Tests
{
    public class DamageAggroBroadcastTests
    {
        [Fact]
        public void PlotAndPeriodicDamageDoNotPublishTheClientAggroTable()
        {
            var policy = typeof(DamageEffect).GetMethod(
                "ShouldBroadcastAggroPacket",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(policy);
            Assert.False((bool)policy.Invoke(null, new object[] { new CastBuff(null) }));
            Assert.False((bool)policy.Invoke(
                null,
                new object[] { new CastPlot(1, 2, 3, 4) }));
            Assert.True((bool)policy.Invoke(
                null,
                new object[] { new CastSkill(1, 2) }));
        }

        [Fact]
        public void PeriodicDamagePublishesItsClientEnvelopeInsideTheTickBatch()
        {
            var policy = typeof(DamageEffect).GetMethod(
                "ShouldBroadcastDamagePacket",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(policy);
            Assert.True((bool)policy.Invoke(null, new object[] { new CastBuff(null) }));
            Assert.True((bool)policy.Invoke(
                null,
                new object[] { new CastPlot(1, 2, 3, 4) }));
            Assert.True((bool)policy.Invoke(
                null,
                new object[] { new CastSkill(1, 2) }));
        }
    }
}
