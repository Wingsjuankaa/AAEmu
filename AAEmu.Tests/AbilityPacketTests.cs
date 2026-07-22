using System.Reflection;

using AAEmu.Game.Core.Packets.C2G;

using Xunit;

namespace AAEmu.Tests
{
    public class AbilityPacketTests
    {
        [Theory]
        [InlineData(0u, 32316u, false, 100.0f, true)]
        [InlineData(32316u, 32316u, false, 100.0f, true)]
        [InlineData(36989u, 32316u, true, 4.0f, true)]
        [InlineData(36989u, 32316u, true, 12.1f, false)]
        [InlineData(36989u, 32316u, false, 4.0f, false)]
        public void SwapAbilityReference_AcceptsSelfOrNearbyNpc(
            uint packetObjId, uint activeObjId, bool isSpawnedNpc, float npcDistance,
            bool expected)
        {
            var validator = typeof(CSSwapAbilityPacket).GetMethod(
                "IsAllowedReference",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.NotNull(validator);
            Assert.Equal(expected, validator.Invoke(
                null,
                new object[] { packetObjId, activeObjId, isSpawnedNpc, npcDistance }));
        }
    }
}
