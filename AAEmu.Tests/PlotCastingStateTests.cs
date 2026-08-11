using System;
using System.Threading.Tasks;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class PlotCastingStateTests
    {
        [Fact]
        public async Task StopCastingCancelsMatchingPlotOnlySkill()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 10752 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            caster.ActivePlotState = state;

            var stopped = await CSStopCastingPacket.TryStopCasting(caster, 0, 123);

            Assert.True(stopped);
            Assert.True(state.CancellationRequested());
            Assert.True(skill.Cancelled);
        }

        [Fact]
        public async Task StopCastingIgnoresDifferentPlotTlId()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 10752 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            caster.ActivePlotState = state;

            var stopped = await CSStopCastingPacket.TryStopCasting(caster, 0, 124);

            Assert.False(stopped);
            Assert.False(state.CancellationRequested());
            Assert.False(skill.Cancelled);
        }

        [Fact]
        public async Task StopCastingUsesPlotTimelineInsteadOfSkillTimeline()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 10752 }) { TlId = 321 };
            var state = new PlotState(caster, null, null, null, null, skill);
            caster.ActivePlotState = state;

            var stopped = await CSStopCastingPacket.TryStopCasting(caster, 123, 321);

            Assert.True(stopped);
            Assert.True(state.CancellationRequested());
            Assert.True(skill.Cancelled);
        }

        [Fact]
        public async Task StopCastingFallsBackToSkillTimelineWhenPlotTimelineIsZero()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 10752 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            caster.ActivePlotState = state;

            var stopped = await CSStopCastingPacket.TryStopCasting(caster, 123, 0);

            Assert.True(stopped);
            Assert.True(state.CancellationRequested());
            Assert.True(skill.Cancelled);
        }

        [Fact]
        public async Task StopCastingReleasesCastingUseablePlotWithoutCancellingIt()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 36470 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent { Id = 24216, Casting = true, CastingUseable = true };
            var started = new DateTime(2026, 8, 7, 0, 0, 0, DateTimeKind.Utc);
            state.BeginCasting(edge, 4000, started);
            caster.ActivePlotState = state;

            var stopped = await CSStopCastingPacket.TryStopCasting(caster, 0, 123);
            state.TryReleaseCastingUseable(started.AddMilliseconds(3000));

            Assert.True(stopped);
            Assert.False(state.CancellationRequested());
            Assert.False(skill.Cancelled);
            Assert.True(state.ShouldRelease(edge));
        }

        [Theory]
        [InlineData(0, 0)]
        [InlineData(999, 24)]
        [InlineData(1000, 25)]
        [InlineData(2999, 74)]
        [InlineData(3000, 75)]
        [InlineData(4000, 100)]
        [InlineData(5000, 100)]
        public void CastingPercentageMatchesAa8InclusiveBands(
            int elapsedMs,
            int expected)
        {
            var started = new DateTime(2026, 8, 7, 0, 0, 0, DateTimeKind.Utc);
            Assert.Equal(
                expected,
                PlotState.CalculateCastingPercent(
                    started, started.AddMilliseconds(elapsedMs), 4000));
        }

        [Theory]
        [InlineData(false, false, false)]
        [InlineData(true, false, true)]
        [InlineData(false, true, true)]
        [InlineData(true, true, true)]
        public void ArrivalCompletesBothNativeCastAndChannelEdges(
            bool casting,
            bool channeling,
            bool expected)
        {
            var edge = new PlotNextEvent
            {
                Casting = casting,
                Channeling = channeling
            };

            Assert.Equal(expected, PlotNode.CompletesCastOrChannel(edge));
        }

        [Fact]
        public void PlotEventAssociatesCasterWithTheEventReachedThroughTheCastEdge()
        {
            var castingEdge = new PlotNextEvent {Casting = true};
            var channelingEdge = new PlotNextEvent {Channeling = true};

            Assert.Equal((uint)0, PlotNode.ResolveCastOwnerId(null, 42));
            Assert.Equal((uint)42, PlotNode.ResolveCastOwnerId(castingEdge, 42));
            Assert.Equal((uint)42, PlotNode.ResolveCastOwnerId(channelingEdge, 42));
        }

        [Fact]
        public void RepeatedStartSkillReleasesMatchingCastingUseablePlot()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 36470 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent { Id = 27749, Casting = true, CastingUseable = true };
            state.BeginCasting(edge, 4000, DateTime.UtcNow.AddMilliseconds(-2000));
            caster.ActivePlotState = state;

            var released = CSStartSkillPacket.TryReleaseActivePlotCast(caster, 36470);

            Assert.True(released);
            Assert.False(state.CancellationRequested());
            Assert.True(state.ShouldRelease(edge));
            Assert.InRange(state.CastingPercent, 49, 51);
        }

        [Fact]
        public void RepeatedStartSkillDoesNotReleaseDifferentActivePlot()
        {
            var caster = new Unit();
            var skill = new Skill(new SkillTemplate { Id = 36470 }) { TlId = 123 };
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent { Id = 27749, Casting = true, CastingUseable = true };
            state.BeginCasting(edge, 4000, DateTime.UtcNow.AddMilliseconds(-2000));
            caster.ActivePlotState = state;

            Assert.False(CSStartSkillPacket.TryReleaseActivePlotCast(caster, 41219));
            Assert.False(state.ShouldRelease(edge));
        }

        [Fact]
        public void Aa8ReleasePacketReleasesObservedActorAndPlotTimeline()
        {
            var caster = new Unit {ObjId = 32667};
            var skill = new Skill(new SkillTemplate {Id = 41219}) {TlId = 6332};
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent {Id = 41647, Casting = true, CastingUseable = true};
            state.BeginCasting(edge, 5000, DateTime.UtcNow.AddMilliseconds(-2500));
            caster.ActivePlotState = state;

            Assert.True(CSReleasePlotCastingPacket.TryRelease(caster, 32667, 6332));
            Assert.True(state.ShouldRelease(edge));
            Assert.InRange(state.CastingPercent, 49, 51);
            Assert.False(CSReleasePlotCastingPacket.TryRelease(caster, 32667, 6332));
        }

        [Fact]
        public void Aa8ReleasePacketDecodesObservedSevenByteBodyWithoutTimelineShift()
        {
            var payload = CSReleasePlotCastingPacket.ReadPayload(new PacketStream(new byte[]
            {
                0x9b, 0x7f, 0x00, // actor ObjId 32667 (bc)
                0x00, 0x00,       // native middle field
                0xbc, 0x18        // plot timeline 6332
            }));

            Assert.Equal((uint)32667, payload.ActorObjId);
            Assert.Equal((ushort)0, payload.Mode);
            Assert.Equal((ushort)6332, payload.PlotTlId);
        }

        [Fact]
        public void Aa8ReleasePacketRejectsForeignActorOrTimeline()
        {
            var caster = new Unit {ObjId = 32667};
            var skill = new Skill(new SkillTemplate {Id = 36470}) {TlId = 6332};
            var state = new PlotState(caster, null, null, null, null, skill);
            var edge = new PlotNextEvent {Id = 27749, Casting = true, CastingUseable = true};
            state.BeginCasting(edge, 4000, DateTime.UtcNow.AddMilliseconds(-1000));
            caster.ActivePlotState = state;

            Assert.False(CSReleasePlotCastingPacket.TryRelease(caster, 1, 6332));
            Assert.False(CSReleasePlotCastingPacket.TryRelease(caster, 32667, 99));
            Assert.False(state.ShouldRelease(edge));
        }
    }
}
