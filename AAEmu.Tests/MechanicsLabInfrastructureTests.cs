using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

using AAEmu.Commons.Cryptography;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;
using AAEmu.Game.Utils.DB;
using AAEmu.MechanicsLab;

using Xunit;

using GameTask = AAEmu.Game.Models.Tasks.Task;

namespace AAEmu.Tests
{
    public class MechanicsLabInfrastructureTests
    {
        [Fact]
        public async Task ManualClockAdvancesWithoutSleeping()
        {
            var start = new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc);
            var clock = new ManualMechanicsClock(start);

            await clock.Delay(TimeSpan.FromSeconds(3));
            clock.Advance(TimeSpan.FromMilliseconds(250));

            Assert.Equal(start.AddMilliseconds(3250), clock.UtcNow);
        }

        [Fact]
        public void ManualSchedulerRunsDeterministicallyAndCancels()
        {
            var clock = new ManualMechanicsClock(
                new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc));
            var scheduler = new ManualMechanicsScheduler(clock);
            var task = new CountingTask();

            scheduler.Schedule(task, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(1), 2);
            clock.Advance(TimeSpan.FromMilliseconds(999));
            Assert.Equal(0, task.Count);
            clock.Advance(TimeSpan.FromMilliseconds(1));
            clock.Advance(TimeSpan.FromSeconds(2));

            Assert.Equal(3, task.Count);
            Assert.Equal(0, scheduler.PendingCount);
            Assert.Equal(3, scheduler.Timeline.Count(entry => entry.Event == "executed"));
        }

        [Fact]
        public void DeterministicRandScopeReplaysTheSameSequence()
        {
            int[] first;
            int[] second;
            using (Rand.PushDeterministicSeed(558734))
                first = Enumerable.Range(0, 8).Select(_ => Rand.Next()).ToArray();
            using (Rand.PushDeterministicSeed(558734))
                second = Enumerable.Range(0, 8).Select(_ => Rand.Next()).ToArray();

            Assert.Equal(first, second);
        }

        [Fact]
        public void SQLiteReadOnlyPathScopeRestoresTheProductionDefault()
        {
            var original = SQLite.DatabasePath;
            var temporary = Path.GetTempFileName();
            try
            {
                using (SQLite.PushReadOnlyDatabasePath(temporary))
                    Assert.Equal(Path.GetFullPath(temporary), SQLite.DatabasePath);
                Assert.Equal(original, SQLite.DatabasePath);
            }
            finally
            {
                File.Delete(temporary);
            }
        }

        [Fact]
        public void ArenaUsesRealUnitsAndDeterministicSpatialQueries()
        {
            var clock = new ManualMechanicsClock(
                new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc));
            var arena = new MechanicsArena(new MechanicsTimeline(clock));
            var ledger = new RecordingPacketLedger(clock);
            var connection = new GameConnection(ledger);
            var character = arena.CreateCharacter(new MechanicsActorSpec
            {
                Id = 1, Kind = "character", X = 0, Y = 0, Z = 0,
                Hp = 100, MaxHp = 100, Mp = 100, MaxMp = 100
            }, connection);
            var near = new MechanicsNpc
            {
                ObjId = 2, TemplateId = 13013, Hp = 100, MaxHp = 100,
                Template = new NpcTemplate {Id = 13013, Scale = 1f}
            };
            near.Transform.Local.SetPosition(3, 4, 0);
            arena.Add(near);
            var far = new MechanicsNpc
            {
                ObjId = 3, TemplateId = 13013, Hp = 100, MaxHp = 100,
                Template = new NpcTemplate {Id = 13013, Scale = 1f}
            };
            far.Transform.Local.SetPosition(30, 0, 0);
            arena.Add(far);

            Assert.Same(near, arena.GetUnit(2));
            Assert.Equal(new uint[] {2}, arena.GetAround(character, 5f, false)
                .Select(item => item.ObjId).ToArray());
        }

        [Fact]
        public void DD05EncodeCaptureAndTransportAreOneOrderedTransaction()
        {
            var clock = new ManualMechanicsClock(
                new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc));
            var ledger = new RecordingPacketLedger(clock);
            var context = new MechanicsRuntimeContext {Clock = clock, PacketObserver = ledger};
            EncryptionManager.Instance.Load();
            var connection = new GameConnection(ledger) {AccountId = 0xAA800001};
            EncryptionManager.Instance.SetSCMessageCount(connection.Id, connection.AccountId, 255);
            ledger.ArmTransportReorderingProbe(TimeSpan.FromMilliseconds(50));

            using (MechanicsRuntime.Push(context))
            {
                Parallel.Invoke(
                    () => connection.SendPacket(new SCUnitPointsPacket(1, 10, 20)),
                    () => connection.SendPacket(new SCUnitPointsPacket(2, 30, 40)));
            }

            var transported = ledger.Entries.OrderBy(entry => entry.TransportSequence).ToList();
            Assert.Equal(new byte[] {255, 0}, transported.Select(entry => entry.Counter.Value).ToArray());
            Assert.All(transported, entry => Assert.True(entry.BodyConsumedExactly));
            Assert.All(transported, entry => Assert.True(entry.WireMatchesPlaintext));
            Assert.Equal(transported.Select(entry => entry.Sequence),
                ledger.Entries.OrderBy(entry => entry.Sequence).Select(entry => entry.Sequence));
        }

        [Fact]
        public void TimelineRecordsProductionPlotEventsThroughTheNarrowSink()
        {
            var clock = new ManualMechanicsClock(
                new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc));
            IMechanicsEventSink sink = new MechanicsTimeline(clock);

            sink.RecordEvent("plot_event", 10, 20, "plot=5732;event=51663");

            var timeline = Assert.IsType<MechanicsTimeline>(sink);
            var entry = Assert.Single(timeline.Events);
            Assert.Equal("plot_event", entry.Event);
            Assert.Equal((uint)10, entry.ActorId);
            Assert.Equal((uint)20, entry.TargetId);
        }

        [Fact]
        public void DeadNpcRejectsTrailingPlotAggroMutation()
        {
            var npc = new Npc {ObjId = 2, Hp = 0, MaxHp = 100};
            var attacker = new Unit {ObjId = 1, Hp = 100, MaxHp = 100};

            npc.OnDamageReceived(attacker, 25);

            Assert.Empty(npc.AggroTable);
            Assert.Null(npc.CurrentTarget);
        }

        private sealed class CountingTask : GameTask
        {
            public int Count { get; private set; }
            public override void Execute() => Count++;
        }
    }
}
