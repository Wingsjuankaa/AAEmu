using System.Collections.Generic;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Heirs;

using Xunit;

namespace AAEmu.Tests
{
    public class Aa8HeirProgressionTests
    {
        private static readonly IReadOnlyList<HeirLevel> Levels = new[]
        {
            new HeirLevel
            {
                Id = 1,
                Level = 0,
                ReqItemId = 40491,
                ReqItemCount = 1,
                ReqTotalExp = 100,
                Step = 0
            },
            new HeirLevel { Id = 2, Level = 1, ReqTotalExp = 250, Step = 1 },
            new HeirLevel { Id = 3, Level = 2, ReqTotalExp = 500, Step = 1 }
        };

        [Fact]
        public void Aa8LevelUpPacketsUseTheNativeOpcodesAndBcOnlyReply()
        {
            var request = new CSHeirLevelUpPacket();
            Assert.Equal((ushort)0x125, request.TypeId);
            Assert.Equal(5, request.Level);

            var actual = new PacketStream();
            var expected = new PacketStream();
            var reply = new SCHeirLevelUpPacket(0x1234);
            reply.Write(actual);
            expected.WriteBc(0x1234);

            Assert.Equal((ushort)0x0AC, reply.TypeId);
            Assert.Equal(5, reply.Level);
            Assert.Equal(expected.GetBytes(), actual.GetBytes());
        }

        [Fact]
        public void PositiveExpStopsOnePointBeforeTheExplicitLevelUpBoundary()
        {
            Assert.Equal((byte)0, HeirProgressionPolicy.GetLevelForExp(Levels, 0));
            Assert.Equal((byte)0, HeirProgressionPolicy.GetLevelForExp(Levels, 99));
            Assert.Equal((byte)1, HeirProgressionPolicy.GetLevelForExp(Levels, 100));
            Assert.Equal(99, HeirProgressionPolicy.ApplyExpGain(Levels, 0, 1000));
            Assert.Equal(99, HeirProgressionPolicy.ApplyExpGain(Levels, 99, 1));
            Assert.Equal(50, HeirProgressionPolicy.ApplyExpGain(Levels, 50, -10));
        }

        [Fact]
        public void ItemlessBoundaryRemainsEligibleForServerCompatibilityTransition()
        {
            Assert.Equal((byte)1, HeirProgressionPolicy.GetLevelForExp(Levels, 249));
            Assert.Equal(249, HeirProgressionPolicy.ApplyExpGain(Levels, 100, 1000));
            Assert.True(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 55, 249, out var requirement));
            Assert.Equal((uint)0, requirement.ReqItemId);
            Assert.Equal((byte)2, HeirProgressionPolicy.GetLevelForExp(
                Levels, requirement.ReqTotalExp));
        }

        [Fact]
        public void RequestRequiresLevelCapAndTheExactExperienceBoundary()
        {
            Assert.False(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 54, 99, out _));
            Assert.False(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 55, 98, out _));

            Assert.True(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 55, 99, out var first));
            Assert.Equal((uint)40491, first.ReqItemId);
            Assert.Equal(1, first.ReqItemCount);

            Assert.False(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 55, 100, out _));
            Assert.False(HeirProgressionPolicy.TryGetLevelUpRequirement(
                Levels, 55, 250, out _));
        }
    }
}
