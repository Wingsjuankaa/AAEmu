using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;
using AAEmu.MechanicsLab;

using Xunit;

namespace AAEmu.Tests
{
    public class UnitCooldownsTests
    {
        private static readonly DateTime Start =
            new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc);

        [Fact]
        public void StartIsDeduplicatedByCastTokenAndNewCastReplaces()
        {
            var clock = new ManualMechanicsClock(Start);
            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                var cooldowns = new UnitCooldowns();
                Assert.True(cooldowns.StartCooldown(11918, 12000, 41));
                clock.Advance(TimeSpan.FromSeconds(2));
                Assert.False(cooldowns.StartCooldown(11918, 12000, 41));
                Assert.Equal(10000, cooldowns.GetRemaining(11918));

                Assert.True(cooldowns.StartCooldown(11918, 12000, 42));
                Assert.Equal(12000, cooldowns.GetRemaining(11918));
            }
        }

        [Fact]
        public void PlotEndSnapshotKeepsLaunchTimeCooldownOrigin()
        {
            var clock = new ManualMechanicsClock(Start);
            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                var character = new Character(null);
                Assert.True(character.Cooldowns.StartCooldown(11918, 12000, 41));

                // The live AA8 trace closes Charge's plot roughly 410 ms after
                // CSStartSkill. A plot-end snapshot must expose the remaining time,
                // not a newly restarted 12-second cooldown.
                clock.Advance(TimeSpan.FromMilliseconds(410));
                var entry = character.Cooldowns.GetSnapshot(clock.UtcNow).Single();

                Assert.Equal(11918u, entry.SkillId);
                Assert.Equal(12000, entry.DurationMilliseconds);
                Assert.Equal(11590, entry.RemainingMilliseconds);
            }
        }

        [Fact]
        public void FlatAndPercentReduceRemainingAndClampToZero()
        {
            var clock = new ManualMechanicsClock(Start);
            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                var cooldowns = new UnitCooldowns();
                cooldowns.StartCooldown(11918, 12000, 1);
                clock.Advance(TimeSpan.FromSeconds(2));

                var flat = cooldowns.ReduceCooldown(CooldownSelector.Skill(11918), 2000, 0);
                Assert.Equal(10000, flat.Entries.Single().PreviousMilliseconds);
                Assert.Equal(8000, cooldowns.GetRemaining(11918));

                cooldowns.ReduceCooldown(CooldownSelector.Skill(11918), 0, 25);
                Assert.Equal(6000, cooldowns.GetRemaining(11918));

                var expired = cooldowns.ReduceCooldown(CooldownSelector.Skill(11918), 9000, 0);
                Assert.True(expired.Entries.Single().Expired);
                Assert.False(cooldowns.CheckCooldown(11918));
            }
        }

        [Fact]
        public void MissingCooldownIsNoOpAndResetIsSeparate()
        {
            var clock = new ManualMechanicsClock(Start);
            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                var cooldowns = new UnitCooldowns();
                Assert.True(cooldowns.ReduceCooldown(
                    CooldownSelector.Skill(11918), 2000, 0).IsNoOp);

                cooldowns.StartCooldown(11918, 12000, 1);
                var reset = cooldowns.ResetCooldown(CooldownSelector.Skill(11918));
                Assert.Equal(12000, reset.Entries.Single().PreviousMilliseconds);
                Assert.Equal(0, cooldowns.GetRemaining(11918));
            }
        }

        [Fact]
        public void ConcurrentDuplicateStartHasOneWinner()
        {
            var clock = new ManualMechanicsClock(Start);
            using (MechanicsRuntime.Push(new MechanicsRuntimeContext {Clock = clock}))
            {
                var cooldowns = new UnitCooldowns();
                var winners = 0;
                Parallel.For(0, 32, _ =>
                {
                    if (cooldowns.StartCooldown(11918, 12000, 77))
                        Interlocked.Increment(ref winners);
                });

                Assert.Equal(1, winners);
                Assert.Equal(12000, cooldowns.GetSnapshot(clock.UtcNow).Single().RemainingMilliseconds);
            }
        }

        [Theory]
        [InlineData(5, 0, true)]
        [InlineData(5, 4, true)]
        [InlineData(5, 5, false)]
        [InlineData(5, 99, false)]
        [InlineData(100, 99, true)]
        public void BleedingProcUsesExactFivePercentBoundary(int chance, int roll, bool expected)
        {
            Assert.Equal(expected, BuffEffect.PassesChance(chance, roll));
        }

        [Fact]
        public void Aa8SpecialType153MapsToReductionNotReset()
        {
            Assert.Equal(153, (int)SpecialType.ReduceCooldown);
            Assert.Equal(nameof(ReduceCooldown), SpecialType.ReduceCooldown.ToString());
            Assert.NotEqual(SpecialType.ResetCooldown, SpecialType.ReduceCooldown);
        }

        [Fact]
        public void Aa8CooldownSnapshotUsesEncryptedLevelFiveTransport()
        {
            var packet = new SCCooldownsPacket(new Character(null));

            Assert.Equal(5, packet.Level);
        }

        [Fact]
        public void Aa8CooldownReductionUsesEncryptedLevelFiveTransport()
        {
            var packet = new SCSkillCooldownReducePacket(
                1, 11918, 0, 0, 1, 2000);

            Assert.Equal(5, packet.Level);
        }
    }
}
