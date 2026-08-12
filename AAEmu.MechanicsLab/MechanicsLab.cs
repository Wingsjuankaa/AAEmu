using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;

using AAEmu.Commons.Cryptography;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.IO;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;
using AAEmu.Game.Utils.DB;

using Newtonsoft.Json;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsUnitSnapshot
    {
        public long Sequence { get; set; }
        public DateTime TimestampUtc { get; set; }
        public string Boundary { get; set; }
        public uint ActorId { get; set; }
        public int Hp { get; set; }
        public int Mp { get; set; }
        public bool Dead { get; set; }
        public uint TargetId { get; set; }
        public float X { get; set; }
        public float Y { get; set; }
        public float Z { get; set; }
        public List<uint> BuffIds { get; set; } = new List<uint>();
        public List<uint> InitialBuffsStillPresent { get; set; } = new List<uint>();
    }

    public sealed class MechanicsValidation
    {
        public string Name { get; set; }
        public bool Passed { get; set; }
        public string Detail { get; set; }
        public bool HasOracle { get; set; } = true;
    }

    public sealed class MechanicsRunResult
    {
        public int SchemaVersion { get; set; } = 1;
        public string Scenario { get; set; }
        public string CompactPath { get; set; }
        public string CompactSha256 { get; set; }
        public string ScenarioSha256 { get; set; }
        public string ResultSha256 { get; set; }
        public DateTime StartedUtc { get; set; }
        public DateTime FinishedUtc { get; set; }
        public List<MechanicsTimelineEvent> Timeline { get; set; }
        public List<MechanicsTaskEvent> Tasks { get; set; }
        public List<PacketLedgerEntry> Packets { get; set; }
        public List<MechanicsUnitSnapshot> Snapshots { get; set; }
        public List<string> Exceptions { get; set; }
        public List<string> InvalidDeadUnitReferences { get; set; }
        public List<MechanicsValidation> Validations { get; set; }
        public int PendingTasks { get; set; }
        public bool Passed => Validations != null && Validations.All(item => item.Passed || !item.HasOracle);
    }

    public sealed class MechanicsLab : IMechanicsExceptionSink
    {
        private bool _runtimeLoaded;
        private readonly string _compactPath;
        private readonly List<string> _exceptions = new List<string>();
        private readonly List<MechanicsUnitSnapshot> _snapshots = new List<MechanicsUnitSnapshot>();
        private long _snapshotSequence;

        public MechanicsLab(string compactPath)
        {
            _compactPath = Path.GetFullPath(compactPath ?? throw new ArgumentNullException(nameof(compactPath)));
        }

        public MechanicsRunResult Run(MechanicsScenario scenario)
        {
            if (scenario == null)
                throw new ArgumentNullException(nameof(scenario));
            if (scenario.SchemaVersion != 1)
                throw new InvalidOperationException($"Unsupported mechanics scenario schema {scenario.SchemaVersion}");

            _exceptions.Clear();
            _snapshots.Clear();
            _snapshotSequence = 0;
            var clock = new ManualMechanicsClock(scenario.ClockUtc);
            var timeline = new MechanicsTimeline(clock);
            var scheduler = new ManualMechanicsScheduler(clock);
            var ledger = new RecordingPacketLedger(clock);
            var arena = new MechanicsArena(timeline);
            var context = new MechanicsRuntimeContext
            {
                Clock = clock,
                Scheduler = scheduler,
                World = arena,
                PacketObserver = ledger,
                DeathSink = arena,
                ExceptionSink = this,
                EventSink = timeline,
                SuppressLoot = false,
                SuppressNpcAi = true,
                ContinueProductionDeathClosure = true,
                BackgroundRunner = action => action()
            };

            var normalizedScenario = JsonConvert.SerializeObject(scenario, Formatting.None);
            var result = new MechanicsRunResult
            {
                Scenario = scenario.Name,
                CompactPath = _compactPath,
                CompactSha256 = HashFile(_compactPath),
                ScenarioSha256 = HashBytes(Encoding.UTF8.GetBytes(normalizedScenario)),
                StartedUtc = clock.UtcNow
            };

            using (SQLite.PushReadOnlyDatabasePath(_compactPath))
            using (Rand.PushDeterministicSeed(scenario.Seed))
            using (MechanicsRuntime.Push(context))
            {
                if (!_runtimeLoaded)
                {
                    LoadRuntimeClosure();
                    _runtimeLoaded = true;
                }
                EncryptionManager.Instance.Load();

                var connection = new GameConnection(ledger)
                {
                    AccountId = 0xAA800001,
                    State = GameState.World
                };
                var actors = CreateActors(scenario, arena, connection);
                var initialBuffIndexes = AddInitialBuffs(scenario, actors);

                ledger.Clear();
                EncryptionManager.Instance.SetSCMessageCount(
                    connection.Id,
                    connection.AccountId,
                    scenario.Dd05Initial);
                timeline.Add("scenario_started", 0, 0, scenario.Name);
                Snapshot("initial", scenario, actors, clock);

                var activeSkills = new Dictionary<uint, Skill>();
                foreach (var action in scenario.Actions)
                {
                    ExecuteAction(action, actors, activeSkills, clock, timeline, connection, ledger);
                    scheduler.RunDue();
                    Snapshot($"after:{action.Type}", scenario, actors, clock);
                }

                result.FinishedUtc = clock.UtcNow;
                result.Timeline = timeline.Events;
                result.Tasks = scheduler.Timeline;
                result.Packets = ledger.Entries;
                result.Snapshots = _snapshots;
                result.Exceptions = _exceptions
                    .Concat(scheduler.Exceptions.Select(exception => exception.ToString()))
                    .ToList();
                result.PendingTasks = scheduler.PendingCount;
                result.InvalidDeadUnitReferences = arena.FindInvalidDeadUnitReferences();
                result.Validations = Validate(
                    scenario,
                    result,
                    actors,
                    arena,
                    initialBuffIndexes);
            }

            result.ResultSha256 = null;
            result.ResultSha256 = HashBytes(Encoding.UTF8.GetBytes(
                JsonConvert.SerializeObject(result, Formatting.None)));
            return result;
        }

        public void RecordException(string boundary, Exception exception)
        {
            _exceptions.Add($"{boundary}: {exception}");
        }

        private static void LoadRuntimeClosure()
        {
            var clientSource = Environment.GetEnvironmentVariable("AA8_CLIENT_SOURCE");
            if (!string.IsNullOrWhiteSpace(clientSource))
            {
                ClientFileManager.ClearSources();
                if (!ClientFileManager.AddSource(clientSource))
                    throw new InvalidOperationException($"Unable to open AA8 client source: {clientSource}");
            }
            GameDataManager.Instance.LoadGameData();
            FormulaManager.Instance.Load();
            ItemManager.Instance.Load();
            NpcManager.Instance.Load();
            DoodadManager.Instance.Load();
            AnimationManager.Instance.Load();
            PlotManager.Instance.Load();
            SkillManager.Instance.Load();
            ExpirienceManager.Instance.Load();
            WorldManager.Instance.LoadAreaShapes();
            // CanAttack consults the declarative zone catalog even for an NPC
            // target.  The flat lab arena does not start WorldManager, but the
            // catalog itself belongs to the compact closure required by combat.
            ZoneManager.Instance.Load(initializeConflictState: false);
        }

        private static Dictionary<uint, Unit> CreateActors(
            MechanicsScenario scenario,
            MechanicsArena arena,
            GameConnection connection)
        {
            var actors = new Dictionary<uint, Unit>();
            foreach (var spec in scenario.Actors)
            {
                Unit actor;
                switch ((spec.Kind ?? string.Empty).ToLowerInvariant())
                {
                    case "character":
                        actor = arena.CreateCharacter(spec, connection);
                        break;
                    case "npc":
                        actor = arena.CreateNpc(spec);
                        break;
                    case "slave":
                        actor = arena.CreateSlave(spec);
                        break;
                    default:
                        throw new InvalidOperationException($"Unsupported actor kind '{spec.Kind}'");
                }
                actors.Add(actor.ObjId, actor);
            }

            foreach (var source in actors.Values)
            foreach (var target in actors.Values.Where(target => target.ObjId != source.ObjId))
                arena.MakeHostile(source, target);
            return actors;
        }

        private static Dictionary<uint, uint> AddInitialBuffs(
            MechanicsScenario scenario,
            IReadOnlyDictionary<uint, Unit> actors)
        {
            var byIndex = new Dictionary<uint, uint>();
            foreach (var buff in scenario.InitialBuffs)
            {
                var owner = RequireActor(actors, buff.ActorId);
                var caster = RequireActor(actors, buff.CasterId == 0 ? buff.ActorId : buff.CasterId);
                owner.Buffs.AddBuff(buff.BuffId, caster);
                var effect = owner.Buffs.GetEffectFromBuffId(buff.BuffId);
                if (effect != null)
                    byIndex[effect.Index] = buff.BuffId;
            }
            return byIndex;
        }

        private static void ExecuteAction(
            MechanicsActionSpec action,
            IReadOnlyDictionary<uint, Unit> actors,
            IDictionary<uint, Skill> activeSkills,
            ManualMechanicsClock clock,
            MechanicsTimeline timeline,
            GameConnection connection,
            RecordingPacketLedger ledger)
        {
            var actionType = (action.Type ?? string.Empty).ToLowerInvariant();
            var actor = action.ActorId == 0 ? null : RequireActor(actors, action.ActorId);
            var target = action.TargetId == 0 ? null : RequireActor(actors, action.TargetId);
            timeline.Add($"action:{actionType}", action.ActorId, action.TargetId, action.SkillId.ToString());
            switch (actionType)
            {
                case "cast":
                    ExecuteCast(action, actor, target, activeSkills, timeline);
                    break;
                case "cast-concurrent":
                    if (actor == null || target == null)
                        throw new InvalidOperationException("cast-concurrent requires actor_id and target_id");
                    ledger.ArmTransportReorderingProbe();
                    var packetTask = Task.Run(() =>
                        connection.SendPacket(new SCUnitPointsPacket(actor.ObjId, actor.Hp, actor.Mp)));
                    if (!ledger.WaitForProbeFirstArrival(TimeSpan.FromSeconds(2)))
                        throw new TimeoutException("Concurrent transport probe did not reach its first DD05 send");
                    var castTask = Task.Run(() =>
                        ExecuteCast(action, actor, target, activeSkills, timeline));
                    Task.WaitAll(castTask, packetTask);
                    break;
                case "release":
                    if (!CSStartSkillPacket.TryReleaseActivePlotCast(actor, action.SkillId))
                        throw new InvalidOperationException($"Skill {action.SkillId} has no releasable active cast");
                    break;
                case "cancel":
                    if (actor?.ActivePlotState == null)
                        throw new InvalidOperationException("cancel requires an active plot");
                    actor.ActivePlotState.RequestCancellation();
                    break;
                case "move":
                    actor.Transform.Local.SetPosition(action.X, action.Y, action.Z, 0f, 0f, 0f);
                    break;
                case "advance":
                    clock.Advance(TimeSpan.FromMilliseconds(action.Milliseconds));
                    break;
                case "start-cooldown":
                    if (actor == null || action.SkillId == 0 || action.Milliseconds <= 0)
                        throw new InvalidOperationException(
                            "start-cooldown requires actor_id, skill_id and positive milliseconds");
                    actor.Cooldowns.StartCooldown(
                        action.SkillId,
                        (uint)action.Milliseconds,
                        (uint)Math.Max(1, action.Value));
                    break;
                case "set-state":
                    if (action.State == "hp") actor.Hp = action.Value;
                    else if (action.State == "mp") actor.Mp = action.Value;
                    else if (action.State == "target") actor.CurrentTarget = target;
                    else throw new InvalidOperationException($"Unsupported state '{action.State}'");
                    break;
                default:
                    throw new InvalidOperationException($"Unsupported action '{action.Type}'");
            }
        }

        private static void ExecuteCast(
            MechanicsActionSpec action,
            Unit actor,
            Unit target,
            IDictionary<uint, Skill> activeSkills,
            MechanicsTimeline timeline)
        {
            if (actor == null)
                throw new InvalidOperationException("cast requires actor_id");
            actor.CurrentTarget = target;
            // The Lab suppresses the NPC behavior loop, but the arena must
            // still model the combat relationship that production AI creates
            // before a lethal transition. DoDie remains responsible for
            // clearing both ends of that relationship.
            if (target is Npc npc)
                npc.CurrentTarget = actor;
            var template = SkillManager.Instance.GetSkillTemplate(action.SkillId) ??
                           throw new InvalidOperationException($"Skill {action.SkillId} is absent from the active compact");
            var skill = new Skill(template, actor);
            activeSkills[actor.ObjId] = skill;
            SkillCastTarget castTarget;
            if (template.TargetType == SkillTargetType.Pos ||
                template.TargetType == SkillTargetType.BallisticPos)
            {
                var targetPosition = target?.Transform.World.Position ?? actor.Transform.World.Position;
                castTarget = new SkillCastPositionTarget
                {
                    PosX = action.X == 0f ? targetPosition.X : action.X,
                    PosY = action.Y == 0f ? targetPosition.Y : action.Y,
                    PosZ = action.Z == 0f ? targetPosition.Z : action.Z,
                    ObjId1 = target?.ObjId ?? 0
                };
            }
            else
            {
                castTarget = new SkillCastUnitTarget(
                    template.TargetType == SkillTargetType.Self
                        ? actor.ObjId
                        : target?.ObjId ?? 0);
            }
            var castResult = skill.Use(
                actor,
                new SkillCasterUnit(actor.ObjId),
                castTarget,
                new SkillObject(),
                true);
            timeline.Add("cast_result", actor.ObjId, target?.ObjId ?? 0, castResult.ToString());
            if (castResult != SkillResult.Success)
                throw new InvalidOperationException($"Skill {action.SkillId} rejected with {castResult}");
        }

        private void Snapshot(
            string boundary,
            MechanicsScenario scenario,
            IReadOnlyDictionary<uint, Unit> actors,
            ManualMechanicsClock clock)
        {
            foreach (var actor in actors.Values.OrderBy(actor => actor.ObjId))
            {
                var goodBuffs = new List<Buff>();
                var badBuffs = new List<Buff>();
                var hiddenBuffs = new List<Buff>();
                actor.Buffs.GetAllBuffs(goodBuffs, badBuffs, hiddenBuffs);
                _snapshots.Add(new MechanicsUnitSnapshot
                {
                    Sequence = ++_snapshotSequence,
                    TimestampUtc = clock.UtcNow,
                    Boundary = boundary,
                    ActorId = actor.ObjId,
                    Hp = actor.Hp,
                    Mp = actor.Mp,
                    Dead = actor.Hp <= 0,
                    TargetId = actor.CurrentTarget?.ObjId ?? 0,
                    InitialBuffsStillPresent = scenario.InitialBuffs
                        .Where(buff => buff.ActorId == actor.ObjId && actor.Buffs.GetBuffCountById(buff.BuffId) > 0)
                        .Select(buff => buff.BuffId)
                        .OrderBy(id => id)
                        .ToList(),
                    X = actor.Transform.World.Position.X,
                    Y = actor.Transform.World.Position.Y,
                    Z = actor.Transform.World.Position.Z,
                    BuffIds = goodBuffs.Concat(badBuffs).Concat(hiddenBuffs)
                        .Where(buff => buff?.Template != null && buff.InUse)
                        .Select(buff => buff.Template.BuffId)
                        .Distinct()
                        .OrderBy(id => id)
                        .ToList()
                });
            }
        }

        private static List<MechanicsValidation> Validate(
            MechanicsScenario scenario,
            MechanicsRunResult result,
            IReadOnlyDictionary<uint, Unit> actors,
            MechanicsArena arena,
            IReadOnlyDictionary<uint, uint> buffIdsByIndex)
        {
            var validations = new List<MechanicsValidation>();
            var levelFive = result.Packets.Where(packet => packet.Level == 5 && packet.Counter.HasValue).ToList();
            var reserved = levelFive.OrderBy(packet => packet.Sequence).ToList();
            var transported = levelFive.OrderBy(packet => packet.TransportSequence ?? long.MaxValue).ToList();
            var reservationCountersOk = AreCountersMonotonic(reserved);
            var transportCountersOk = levelFive.All(packet => packet.TransportSequence.HasValue) &&
                                      AreCountersMonotonic(transported);
            validations.Add(Check("dd05_counter_monotonic_modulo_256",
                !scenario.Expected.RequireCounterMonotonicModulo256 || transportCountersOk,
                string.Join(",", transported.Select(packet => packet.Counter.Value))));
            validations.Add(Check("dd05_counter_reservation_monotonic_modulo_256",
                reservationCountersOk,
                string.Join(",", reserved.Select(packet => packet.Counter.Value))));

            var assignmentMatchesSend = reserved.Select(packet => packet.Sequence)
                .SequenceEqual(transported.Select(packet => packet.Sequence));
            validations.Add(Check("wire_plaintext_order_and_payload",
                !scenario.Expected.RequireWirePlaintextOrderMatch ||
                (levelFive.All(packet => packet.WireMatchesPlaintext) && assignmentMatchesSend),
                $"checked={levelFive.Count}; assignment_matches_send={assignmentMatchesSend}"));
            validations.Add(Check("known_packet_body_consumed_exactly",
                levelFive.All(packet => packet.BodyConsumedExactly),
                $"checked={levelFive.Count}"));

            var packetNames = result.Packets.Select(packet => packet.Packet).ToList();
            var cursor = -1;
            var sequenceOk = true;
            foreach (var expected in scenario.Expected.PacketSequence)
            {
                cursor = packetNames.FindIndex(cursor + 1, packet => packet == expected);
                if (cursor >= 0)
                    continue;
                sequenceOk = false;
                break;
            }
            validations.Add(Check("packet_sequence", sequenceOk,
                string.Join(" -> ", scenario.Expected.PacketSequence)));

            foreach (var expected in scenario.Expected.PacketCounts)
            {
                var actual = result.Packets.Count(packet => packet.Packet == expected.Key);
                validations.Add(Check(
                    $"packet_count:{expected.Key}",
                    actual == expected.Value,
                    $"expected={expected.Value}; actual={actual}"));
            }

            var timelineNames = result.Timeline.Select(entry => entry.Event).ToList();
            cursor = -1;
            var timelineSequenceOk = true;
            foreach (var expected in scenario.Expected.TimelineSequence)
            {
                cursor = timelineNames.FindIndex(cursor + 1, item => item == expected);
                if (cursor >= 0)
                    continue;
                timelineSequenceOk = false;
                break;
            }
            validations.Add(Check("timeline_sequence", timelineSequenceOk,
                string.Join(" -> ", scenario.Expected.TimelineSequence)));

            foreach (var expected in scenario.Expected.TimelineEventCounts)
            {
                var actual = result.Timeline.Count(entry => entry.Event == expected.Key);
                validations.Add(Check(
                    $"timeline_event_count:{expected.Key}",
                    actual == expected.Value,
                    $"expected={expected.Value}; actual={actual}"));
            }

            if (scenario.Expected.CooldownReductionCount.HasValue)
            {
                var actualCount = result.Timeline.Count(entry => entry.Event == "cooldown_reduced");
                validations.Add(Check(
                    "cooldown_reduction_count",
                    actualCount == scenario.Expected.CooldownReductionCount.Value,
                    $"actual={actualCount}"));
            }

            if (scenario.Expected.CooldownRemainingMilliseconds.Count > 0)
            {
                var cooldownActorId = scenario.Expected.CooldownActorId != 0
                    ? scenario.Expected.CooldownActorId
                    : scenario.Actions.First(action => action.ActorId != 0).ActorId;
                actors.TryGetValue(cooldownActorId, out var cooldownActor);
                foreach (var expected in scenario.Expected.CooldownRemainingMilliseconds)
                {
                    var actualRemaining = cooldownActor?.Cooldowns.GetRemaining(expected.Key) ?? 0;
                    validations.Add(Check(
                        $"cooldown_remaining_{expected.Key}",
                        actualRemaining == expected.Value,
                        $"actual={actualRemaining};expected={expected.Value}"));
                }
            }

            var deathIndex = packetNames.FindIndex(name => name == "SCUnitDeathPacket");
            if (deathIndex >= 0)
            {
                var zeroPointsIndex = result.Packets
                    .Select((packet, index) => new {packet, index})
                    .Where(item => item.index > deathIndex)
                    .Where(item => item.packet.Packet == "SCUnitPointsPacket" &&
                                   item.packet.UnitPointsHealth == 0 &&
                                   item.packet.UnitPointsMana == 0)
                    .Select(item => item.index)
                    .DefaultIfEmpty(-1)
                    .First();
                var damageIndex = zeroPointsIndex >= 0
                    ? packetNames.FindIndex(zeroPointsIndex + 1,
                        name => name == "SCUnitDamagedPacket")
                    : -1;
                validations.Add(Check("stable_lethal_closure_order",
                    zeroPointsIndex > deathIndex && damageIndex > zeroPointsIndex,
                    $"death={deathIndex}; hp0={zeroPointsIndex}; damage={damageIndex}"));

                var positiveAggroAfterDeath = result.Packets
                    .Skip(deathIndex + 1)
                    .Where(packet => packet.Packet == "SCUnitAiAggroPacket" && packet.AggroCount > 0)
                    .ToList();
                validations.Add(Check(
                    "no_positive_aggro_after_death",
                    positiveAggroAfterDeath.Count == 0,
                    string.Join(",", positiveAggroAfterDeath.Select(packet =>
                        $"owner={packet.AggroOwnerId};count={packet.AggroCount};seq={packet.Sequence}"))));
            }
            var absentAfterDeath = deathIndex < 0 || scenario.Expected.PacketAbsentAfterDeath.All(
                absent => !packetNames.Skip(deathIndex + 1).Contains(absent));
            validations.Add(Check("packet_absence_after_death", absentAfterDeath,
                string.Join(",", scenario.Expected.PacketAbsentAfterDeath)));

            if (scenario.Expected.DeathCount.HasValue)
            {
                validations.Add(Check("death_count",
                    arena.NpcDeathCount == scenario.Expected.DeathCount.Value,
                    $"actual={arena.NpcDeathCount}"));
                validations.Add(Check("aggro_cleanup_once",
                    arena.AggroCleanupCount == scenario.Expected.DeathCount.Value,
                    $"actual={arena.AggroCleanupCount}"));
                validations.Add(Check("target_cleanup_once",
                    arena.TargetCleanupCount == scenario.Expected.DeathCount.Value,
                    $"actual={arena.TargetCleanupCount}"));
            }

            if (scenario.Expected.TargetHp.HasValue)
            {
                var targetId = scenario.Actions.LastOrDefault(action => action.TargetId != 0)?.TargetId ?? 0;
                validations.Add(Check("target_hp",
                    actors.TryGetValue(targetId, out var target) && target.Hp == scenario.Expected.TargetHp.Value,
                    actors.TryGetValue(targetId, out var actual) ? $"actual={actual.Hp}" : "target missing"));
            }

            var finalTargetId = scenario.Actions.LastOrDefault(action => action.TargetId != 0)?.TargetId ?? 0;
            if (scenario.Expected.MinimumDamage.HasValue)
            {
                var initialTarget = result.Snapshots.FirstOrDefault(snapshot =>
                    snapshot.Boundary == "initial" && snapshot.ActorId == finalTargetId);
                var finalTarget = result.Snapshots.LastOrDefault(snapshot =>
                    snapshot.ActorId == finalTargetId);
                var damage = initialTarget == null || finalTarget == null
                    ? 0
                    : initialTarget.Hp - finalTarget.Hp;
                validations.Add(Check("minimum_damage",
                    damage >= scenario.Expected.MinimumDamage.Value,
                    $"actual={damage}"));
            }

            foreach (var skillId in scenario.Expected.DamageSkillIdsAbsent)
            {
                var matchingPackets = result.Packets
                    .Where(packet => packet.Packet == "SCUnitDamagedPacket" &&
                                     packet.UnitDamagedSkillId == skillId)
                    .ToList();
                var matchingCalculations = result.Timeline
                    .Where(entry => entry.Event == "damage_calculated" &&
                                    ($" {entry.Detail} ").Contains($" skill={skillId} "))
                    .ToList();
                validations.Add(Check(
                    $"damage_skill_absent:{skillId}",
                    matchingPackets.Count == 0 && matchingCalculations.Count == 0,
                    $"packets={matchingPackets.Count};calculations={matchingCalculations.Count}"));
            }

            var casterId = scenario.Actions.FirstOrDefault(action => action.ActorId != 0)?.ActorId ?? 0;
            foreach (var buffId in scenario.Expected.CasterBuffIds)
                validations.Add(Check($"caster_buff_present:{buffId}",
                    actors.TryGetValue(casterId, out var caster) &&
                    caster.Buffs.GetBuffCountById(buffId) > 0,
                    null));
            foreach (var buffId in scenario.Expected.CasterAbsentBuffIds)
                validations.Add(Check($"caster_buff_absent:{buffId}",
                    actors.TryGetValue(casterId, out var caster) &&
                    caster.Buffs.GetBuffCountById(buffId) == 0,
                    null));
            foreach (var buffId in scenario.Expected.TargetBuffIds)
                validations.Add(Check($"target_buff_present:{buffId}",
                    actors.TryGetValue(finalTargetId, out var buffTarget) &&
                    buffTarget.Buffs.GetBuffCountById(buffId) > 0,
                    null));

            if (scenario.Expected.RequireTargetDisplacement)
            {
                var targetSnapshots = result.Snapshots
                    .Where(snapshot => snapshot.ActorId == finalTargetId)
                    .ToList();
                var initialPosition = targetSnapshots.FirstOrDefault();
                var finalPosition = targetSnapshots.LastOrDefault();
                var displaced = initialPosition != null && finalPosition != null &&
                    (Math.Abs(initialPosition.X - finalPosition.X) > 0.01f ||
                     Math.Abs(initialPosition.Y - finalPosition.Y) > 0.01f ||
                     Math.Abs(initialPosition.Z - finalPosition.Z) > 0.01f);
                validations.Add(Check("target_displacement", displaced,
                    initialPosition == null || finalPosition == null
                        ? "target snapshots missing"
                        : $"from=({initialPosition.X},{initialPosition.Y},{initialPosition.Z}); " +
                          $"to=({finalPosition.X},{finalPosition.Y},{finalPosition.Z})"));
            }

            foreach (var buffId in scenario.Expected.RemovedBuffIds)
            {
                var indexes = buffIdsByIndex.Where(pair => pair.Value == buffId).Select(pair => pair.Key).ToList();
                var removeCount = result.Packets.Count(packet =>
                    packet.Packet == "SCBuffRemovedPacket" &&
                    packet.RuntimeBuffIndex.HasValue &&
                    indexes.Contains(packet.RuntimeBuffIndex.Value));
                validations.Add(Check($"remove_on_death_once:{buffId}", removeCount == 1,
                    $"actual={removeCount}"));
            }

            var deathSnapshot = result.Snapshots.FirstOrDefault(snapshot => snapshot.Dead);
            if (deathSnapshot != null)
            {
                var deadMutated = result.Snapshots
                    .Where(snapshot => snapshot.ActorId == deathSnapshot.ActorId && snapshot.Sequence > deathSnapshot.Sequence)
                    .Any(snapshot => snapshot.Hp != 0 || snapshot.InitialBuffsStillPresent.Count > 0);
                validations.Add(Check("no_post_death_unit_mutation", !deadMutated, null));
            }

            if (scenario.Expected.DeathCount.HasValue)
                validations.Add(Check("experience_event_once", arena.ExperienceEvents == 1,
                    $"actual={arena.ExperienceEvents}"));
            validations.Add(Check("no_invalid_dead_unit_references",
                result.InvalidDeadUnitReferences.Count == 0,
                string.Join(" | ", result.InvalidDeadUnitReferences)));
            if (scenario.Expected.PendingTasks.HasValue)
                validations.Add(Check("pending_lab_tasks",
                    result.PendingTasks == scenario.Expected.PendingTasks.Value,
                    $"expected={scenario.Expected.PendingTasks.Value}; actual={result.PendingTasks}"));
            validations.Add(Check("no_exceptions",
                !scenario.Expected.RequireNoExceptions || result.Exceptions.Count == 0,
                string.Join(" | ", result.Exceptions)));
            return validations;
        }

        private static bool AreCountersMonotonic(IReadOnlyList<PacketLedgerEntry> packets)
        {
            for (var index = 1; index < packets.Count; index++)
                if (packets[index].Counter.Value != unchecked((byte)(packets[index - 1].Counter.Value + 1)))
                    return false;
            return true;
        }

        private static MechanicsValidation Check(string name, bool passed, string detail) =>
            new MechanicsValidation {Name = name, Passed = passed, Detail = detail};

        private static Unit RequireActor(IReadOnlyDictionary<uint, Unit> actors, uint id)
        {
            if (!actors.TryGetValue(id, out var actor))
                throw new InvalidOperationException($"Actor {id} is not defined");
            return actor;
        }

        private static string HashFile(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", string.Empty);
        }

        private static string HashBytes(byte[] bytes)
        {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", string.Empty);
        }
    }
}
