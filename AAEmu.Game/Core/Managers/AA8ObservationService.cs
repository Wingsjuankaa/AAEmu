using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using AAEmu.Commons.IO;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Observations;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    public sealed class AA8ObservationService : Singleton<AA8ObservationService>
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly ConcurrentDictionary<uint, ObservationSession> _sessions =
            new ConcurrentDictionary<uint, ObservationSession>();
        private readonly AsyncLocal<ObservationContext> _context =
            new AsyncLocal<ObservationContext>();
        private readonly AsyncLocal<PendingPacket> _pendingPacket =
            new AsyncLocal<PendingPacket>();
        private AA8ObservationStore _store;
        private string _compactSha256 = string.Empty;
        private string _serverBuild = string.Empty;
        private int _unknownPrefixBytes = 256;

        public bool Available { get; private set; }

        public bool HasActiveSession(Character character)
        {
            return TryGetSession(character, out _);
        }

        public void Initialize()
        {
            if (Available)
                return;

            var config = AppConfiguration.Instance.AA8Observation;
            if (config == null || !config.Enabled)
            {
                Log.Info("[AA8Observation] Recorder is disabled by configuration.");
                return;
            }

            var path = config.DatabasePath;
            if (!Path.IsPathRooted(path))
                path = Path.Combine(FileManager.AppPath, path);

            try
            {
                NativeQuestRuntimeCatalogService.Instance.Load();
                _compactSha256 = ComputeFileSha256(
                    Path.Combine(FileManager.AppPath, "Data", "compact.sqlite3"));
                _serverBuild =
                    Assembly.GetExecutingAssembly().GetName().Version?.ToString() ??
                    "unknown";
                _unknownPrefixBytes = Math.Max(
                    0,
                    Math.Min(256, config.UnknownPayloadPrefixBytes));
                _store = new AA8ObservationStore(
                    path,
                    config.QueueCapacity,
                    config.BatchSize,
                    config.FlushIntervalMs);
                _store.Start();
                Available = true;
                Log.Info(
                    "[AA8Observation] Ready at {0}; compact={1}",
                    _store.DatabasePath,
                    _compactSha256);
            }
            catch (Exception ex)
            {
                Log.Error(ex, "[AA8Observation] Failed to initialize recorder.");
                _store?.Dispose();
                _store = null;
            }
        }

        public bool StartSession(
            Character character,
            string label,
            out string sessionId,
            out string error,
            string parentSessionId = null)
        {
            sessionId = string.Empty;
            error = string.Empty;
            if (!Available)
            {
                error = "recorder_unavailable";
                return false;
            }
            if (character == null)
            {
                error = "missing_character";
                return false;
            }
            if (_sessions.ContainsKey(character.Id))
            {
                error = "session_already_active";
                return false;
            }

            var session = new ObservationSession
            {
                SessionId = Guid.NewGuid().ToString("N"),
                ParentSessionId = parentSessionId ?? string.Empty,
                Label = NormalizeText(label, 120, "manual-test"),
                Character = character,
                DroppedAtStart = _store.DroppedEvents
            };
            if (!_sessions.TryAdd(character.Id, session))
            {
                error = "session_already_active";
                return false;
            }

            var config = AppConfiguration.Instance.AA8Observation;
            _store.TryEnqueue(
                @"INSERT INTO observation_sessions(
session_id,parent_session_id,label,character_id,character_name,race,level,
network_session_id,server_build,compact_sha256,forensic_graph_sha256,
started_utc,dropped_events)
VALUES($id,$parent,$label,$characterId,$characterName,$race,$level,
$networkId,$build,$compact,$graph,$started,0)",
                ("$id", session.SessionId),
                ("$parent", NullIfEmpty(session.ParentSessionId)),
                ("$label", session.Label),
                ("$characterId", character.Id),
                ("$characterName", character.Name),
                ("$race", (int)character.Race),
                ("$level", character.Level),
                ("$networkId", character.Connection?.Id ?? 0u),
                ("$build", _serverBuild),
                ("$compact", _compactSha256),
                ("$graph", config.ForensicGraphSha256 ?? string.Empty),
                ("$started", UtcNow()));

            RecordSnapshot(session, "start");
            sessionId = session.SessionId;
            return true;
        }

        public bool ResumeSession(
            Character character,
            string parentSessionId,
            out string sessionId,
            out bool persisted,
            out string error)
        {
            sessionId = string.Empty;
            persisted = false;
            error = string.Empty;
            if (!Available)
            {
                error = "recorder_unavailable";
                return false;
            }

            var expected = _store.ReadLatestSnapshot(parentSessionId);
            if (string.IsNullOrEmpty(expected))
            {
                error = "parent_snapshot_not_found";
                return false;
            }

            if (!StartSession(
                    character,
                    $"resume-{parentSessionId.Substring(0, Math.Min(12, parentSessionId.Length))}",
                    out sessionId,
                    out error,
                    parentSessionId))
                return false;

            if (_sessions.TryGetValue(character.Id, out var session))
            {
                RestoreTouchedItems(session, expected);
                var actual = SnapshotCharacter(session);
                persisted = string.Equals(expected, actual, StringComparison.Ordinal);
                RecordEvent(
                    character,
                    "persistence",
                    persisted ? "persisted" : "blocked",
                    "resume_compare",
                    0,
                    0,
                    null,
                    0,
                    null,
                    0,
                    expected,
                    actual,
                    persisted ? null : "snapshot_mismatch");
            }
            return true;
        }

        public bool StopSession(
            Character character,
            string reason,
            bool cleanDisconnect,
            out string sessionId)
        {
            sessionId = string.Empty;
            if (character == null ||
                !_sessions.TryRemove(character.Id, out var session))
                return false;

            sessionId = session.SessionId;
            RecordSnapshot(session, reason);
            _store.TryEnqueue(
                @"UPDATE observation_sessions
SET ended_utc=$ended,end_reason=$reason,clean_disconnect=$clean,
dropped_events=$dropped,notes=$notes
WHERE session_id=$id",
                ("$ended", UtcNow()),
                ("$reason", NormalizeText(reason, 240, "manual-stop")),
                ("$clean", cleanDisconnect ? 1 : 0),
                ("$dropped", _store.DroppedEvents - session.DroppedAtStart),
                ("$notes", string.Empty),
                ("$id", session.SessionId));
            _store.Flush(TimeSpan.FromSeconds(5));
            return true;
        }

        public void OnDisconnect(Character character)
        {
            StopSession(character, "disconnect_after_save", true, out _);
        }

        public bool Continue(Character character, string note, out string error)
        {
            error = string.Empty;
            if (!TryGetSession(character, out var session))
            {
                error = "no_active_session";
                return false;
            }
            if (!session.Gate.Continue())
            {
                error = "interaction_still_running";
                return false;
            }

            RecordDirectEvent(
                session,
                session.Gate.LastInteractionId,
                "control",
                "expected",
                "continue",
                0,
                0,
                null,
                0,
                null,
                0,
                null,
                JsonConvert.SerializeObject(new { note = NormalizeText(note, 500, string.Empty) }),
                null,
                null);
            return true;
        }

        public bool Mark(
            Character character,
            bool success,
            string note,
            out string error)
        {
            error = string.Empty;
            if (!TryGetSession(character, out var session))
            {
                error = "no_active_session";
                return false;
            }

            RecordDirectEvent(
                session,
                session.Gate.LastInteractionId,
                "client",
                "client_seen",
                success ? "mark_ok" : "mark_fail",
                0,
                0,
                null,
                0,
                null,
                0,
                null,
                JsonConvert.SerializeObject(new
                {
                    success,
                    note = NormalizeText(note, 1000, string.Empty)
                }),
                success ? null : "client_visible_failure",
                null);
            return true;
        }

        public AA8ObservationStatus GetStatus(Character character)
        {
            if (!TryGetSession(character, out var session))
            {
                return new AA8ObservationStatus
                {
                    Available = Available,
                    Active = false,
                    QueueDepth = _store?.QueueDepth ?? 0,
                    DroppedEvents = _store?.DroppedEvents ?? 0
                };
            }

            return new AA8ObservationStatus
            {
                Available = Available,
                Active = true,
                GateOpen = session.Gate.IsOpen,
                SessionId = session.SessionId,
                LastInteractionId = session.Gate.LastInteractionId,
                Label = session.Label,
                QueueDepth = _store.QueueDepth,
                DroppedEvents = _store.DroppedEvents - session.DroppedAtStart
            };
        }

        public AA8ObservationInteraction BeginInteraction(
            Character character,
            string operation,
            uint questId,
            string expectedJson = null)
        {
            if (!TryGetSession(character, out var session))
                return AA8ObservationInteraction.NoopAllowed;

            var existing = _context.Value;
            if (existing != null && existing.CharacterId == character.Id)
                return AA8ObservationInteraction.Nested(existing.InteractionId);

            var interactionId = Guid.NewGuid().ToString("N");
            var sequence = Interlocked.Increment(ref session.InteractionSequence);
            var now = UtcNow();
            if (!session.Gate.TryBegin(interactionId))
            {
                InsertInteraction(
                    session,
                    interactionId,
                    sequence,
                    operation,
                    questId,
                    now,
                    "blocked_by_observer",
                    expectedJson,
                    null,
                    now);
                PersistPendingPacket(session, interactionId);
                RecordDirectEvent(
                    session,
                    interactionId,
                    "control",
                    "blocked",
                    operation,
                    questId,
                    0,
                    null,
                    0,
                    null,
                    0,
                    expectedJson,
                    null,
                    "observer_gate_closed",
                    null);
                character.SendMessage(
                    "[AA8Observe] Interaction blocked. Inspect the previous result, then use /aa8observe continue.");
                return AA8ObservationInteraction.Blocked(interactionId);
            }

            InsertInteraction(
                session,
                interactionId,
                sequence,
                operation,
                questId,
                now,
                null,
                expectedJson,
                null,
                null);
            PersistPendingPacket(session, interactionId);
            _context.Value = new ObservationContext
            {
                CharacterId = character.Id,
                SessionId = session.SessionId,
                InteractionId = interactionId
            };
            return new AA8ObservationInteraction(
                true,
                interactionId,
                false,
                outcome => EndInteraction(session, interactionId, outcome));
        }

        public IDisposable BeginPacket(
            Character character,
            ushort opcode,
            byte level,
            PacketStream stream)
        {
            if (!TryGetSession(character, out _))
                return EmptyDisposable.Instance;

            var previous = _pendingPacket.Value;
            _pendingPacket.Value = new PendingPacket
            {
                Direction = "C2S",
                Opcode = opcode,
                Level = level,
                Bytes = stream?.GetBytes() ?? Array.Empty<byte>()
            };
            return new DelegateDisposable(() => _pendingPacket.Value = previous);
        }

        public void RecordOutboundPacket(
            Character character,
            ushort opcode,
            byte level,
            byte[] bytes)
        {
            if (!TryGetSession(character, out var session))
                return;
            var context = _context.Value;
            if (context == null || context.CharacterId != character.Id)
                return;
            InsertPacket(
                session,
                context.InteractionId,
                "S2C",
                opcode,
                level,
                bytes ?? Array.Empty<byte>(),
                false,
                null);
        }

        public void RecordUnknownPacket(
            Character character,
            uint opcode,
            byte level,
            byte[] bytes)
        {
            if (!TryGetSession(character, out var session))
                return;

            var interactionId = Guid.NewGuid().ToString("N");
            var sequence = Interlocked.Increment(ref session.InteractionSequence);
            var now = UtcNow();
            var acquiredGate = session.Gate.TryBegin(interactionId);
            InsertInteraction(
                session,
                interactionId,
                sequence,
                "unknown_packet",
                0,
                now,
                acquiredGate ? "blocked_unknown_packet" : "blocked_while_paused",
                null,
                null,
                now);
            var prefixLength = Math.Min(_unknownPrefixBytes, bytes?.Length ?? 0);
            var prefix = prefixLength == 0
                ? null
                : BitConverter.ToString(bytes, 0, prefixLength).Replace("-", string.Empty);
            InsertPacket(
                session,
                interactionId,
                "C2S",
                opcode,
                level,
                bytes ?? Array.Empty<byte>(),
                true,
                prefix);
            RecordDirectEvent(
                session,
                interactionId,
                "protocol",
                "blocked",
                "unknown_packet",
                0,
                0,
                null,
                0,
                "packet",
                opcode,
                null,
                null,
                "unknown_opcode",
                null);
            if (acquiredGate)
                session.Gate.Complete(interactionId);
        }

        public void RecordQuestCatalog(Character character, uint questId)
        {
            var entry = NativeQuestRuntimeCatalogService.Instance.Get(questId);
            TouchItems(character, entry.ItemIdsJson);
            RecordEvent(
                character,
                "catalog",
                "expected",
                "quest_catalog_lookup",
                questId,
                0,
                null,
                0,
                "quest_catalog",
                questId,
                JsonConvert.SerializeObject(entry),
                null,
                entry.State == "absent" ? "quest_not_confirmed_native" :
                entry.State == "quarantined" ? "quest_template_quarantined" : null);
        }

        public void RecordEvent(
            Character character,
            string phase,
            string status,
            string operation,
            uint questId = 0,
            uint componentId = 0,
            string actType = null,
            uint detailId = 0,
            string dependencyKind = null,
            long dependencyId = 0,
            string expectedJson = null,
            string actualJson = null,
            string blockerCode = null,
            Exception exception = null)
        {
            if (!TryGetSession(character, out var session))
                return;
            var context = _context.Value;
            RecordDirectEvent(
                session,
                context?.InteractionId,
                phase,
                status,
                operation,
                questId,
                componentId,
                actType,
                detailId,
                dependencyKind,
                dependencyId,
                expectedJson,
                actualJson,
                blockerCode,
                exception == null ? null : NormalizeText(exception.ToString(), 2000, string.Empty));
        }

        public void RecordCurrentEvent(
            string phase,
            string status,
            string operation,
            uint questId = 0,
            uint componentId = 0,
            string actType = null,
            uint detailId = 0,
            string dependencyKind = null,
            long dependencyId = 0,
            string expectedJson = null,
            string actualJson = null,
            string blockerCode = null,
            Exception exception = null)
        {
            var context = _context.Value;
            if (context == null ||
                !_sessions.TryGetValue(context.CharacterId, out var session))
                return;
            RecordDirectEvent(
                session,
                context.InteractionId,
                phase,
                status,
                operation,
                questId,
                componentId,
                actType,
                detailId,
                dependencyKind,
                dependencyId,
                expectedJson,
                actualJson,
                blockerCode,
                exception == null
                    ? null
                    : NormalizeText(exception.ToString(), 2000, string.Empty));
        }

        public void TouchCurrentItem(uint itemId)
        {
            var context = _context.Value;
            if (itemId == 0 ||
                context == null ||
                !_sessions.TryGetValue(context.CharacterId, out var session))
                return;
            session.TouchedItemIds.TryAdd(itemId, true);
        }

        public void TouchItem(Character character, uint itemId)
        {
            if (itemId == 0 || !TryGetSession(character, out var session))
                return;
            session.TouchedItemIds.TryAdd(itemId, true);
        }

        public void Shutdown()
        {
            if (!Available)
                return;

            foreach (var session in _sessions.Values.ToArray())
                StopSession(session.Character, "server_shutdown", true, out _);
            _store.Stop(TimeSpan.FromSeconds(10));
            Available = false;
        }

        private void EndInteraction(
            ObservationSession session,
            string interactionId,
            string outcome)
        {
            session.Gate.Complete(interactionId);
            _context.Value = null;
            _store.TryEnqueue(
                @"UPDATE observation_interactions
SET ended_utc=$ended,outcome=$outcome
WHERE interaction_id=$id",
                ("$ended", UtcNow()),
                ("$outcome", NormalizeText(outcome, 120, "recorded")),
                ("$id", interactionId));
        }

        private void InsertInteraction(
            ObservationSession session,
            string interactionId,
            long sequence,
            string operation,
            uint questId,
            string started,
            string outcome,
            string expectedJson,
            string actualJson,
            string ended)
        {
            _store.TryEnqueue(
                @"INSERT INTO observation_interactions(
interaction_id,session_id,sequence_no,operation,quest_id,started_utc,
ended_utc,outcome,expected_json,actual_json)
VALUES($id,$session,$sequence,$operation,$quest,$started,$ended,$outcome,$expected,$actual)",
                ("$id", interactionId),
                ("$session", session.SessionId),
                ("$sequence", sequence),
                ("$operation", NormalizeText(operation, 120, "unknown")),
                ("$quest", questId == 0 ? (object)DBNull.Value : questId),
                ("$started", started),
                ("$ended", NullIfEmpty(ended)),
                ("$outcome", NullIfEmpty(outcome)),
                ("$expected", NullIfEmpty(expectedJson)),
                ("$actual", NullIfEmpty(actualJson)));
        }

        private void RecordDirectEvent(
            ObservationSession session,
            string interactionId,
            string phase,
            string status,
            string operation,
            uint questId,
            uint componentId,
            string actType,
            uint detailId,
            string dependencyKind,
            long dependencyId,
            string expectedJson,
            string actualJson,
            string blockerCode,
            string exceptionSummary)
        {
            var sequence = Interlocked.Increment(ref session.EventSequence);
            _store.TryEnqueue(
                @"INSERT INTO observation_events(
event_id,session_id,interaction_id,sequence_no,captured_utc,phase,status,
operation,quest_id,component_id,act_type,detail_id,dependency_kind,
dependency_id,expected_json,actual_json,blocker_code,exception_summary)
VALUES($id,$session,$interaction,$sequence,$captured,$phase,$status,
$operation,$quest,$component,$act,$detail,$dependencyKind,$dependencyId,
$expected,$actual,$blocker,$exception)",
                ("$id", Guid.NewGuid().ToString("N")),
                ("$session", session.SessionId),
                ("$interaction", NullIfEmpty(interactionId)),
                ("$sequence", sequence),
                ("$captured", UtcNow()),
                ("$phase", NormalizeText(phase, 80, "runtime")),
                ("$status", NormalizeText(status, 80, "attempted")),
                ("$operation", NormalizeText(operation, 160, "unknown")),
                ("$quest", questId == 0 ? (object)DBNull.Value : questId),
                ("$component", componentId == 0 ? (object)DBNull.Value : componentId),
                ("$act", NullIfEmpty(actType)),
                ("$detail", detailId == 0 ? (object)DBNull.Value : detailId),
                ("$dependencyKind", NullIfEmpty(dependencyKind)),
                ("$dependencyId", dependencyId == 0 ? (object)DBNull.Value : dependencyId),
                ("$expected", NullIfEmpty(expectedJson)),
                ("$actual", NullIfEmpty(actualJson)),
                ("$blocker", NullIfEmpty(blockerCode)),
                ("$exception", NullIfEmpty(exceptionSummary)));
        }

        private void PersistPendingPacket(
            ObservationSession session,
            string interactionId)
        {
            var packet = _pendingPacket.Value;
            if (packet == null || packet.Persisted)
                return;
            packet.Persisted = true;
            InsertPacket(
                session,
                interactionId,
                packet.Direction,
                packet.Opcode,
                packet.Level,
                packet.Bytes,
                false,
                null);
        }

        private void InsertPacket(
            ObservationSession session,
            string interactionId,
            string direction,
            uint opcode,
            byte level,
            byte[] bytes,
            bool unknown,
            string prefix)
        {
            bytes = bytes ?? Array.Empty<byte>();
            _store.TryEnqueue(
                @"INSERT INTO observation_packets(
packet_id,session_id,interaction_id,captured_utc,direction,opcode,level,
size,sha256,is_unknown,payload_prefix_hex)
VALUES($id,$session,$interaction,$captured,$direction,$opcode,$level,
$size,$sha,$unknown,$prefix)",
                ("$id", Guid.NewGuid().ToString("N")),
                ("$session", session.SessionId),
                ("$interaction", NullIfEmpty(interactionId)),
                ("$captured", UtcNow()),
                ("$direction", direction),
                ("$opcode", opcode),
                ("$level", level),
                ("$size", bytes.Length),
                ("$sha", ComputeSha256(bytes)),
                ("$unknown", unknown ? 1 : 0),
                ("$prefix", NullIfEmpty(prefix)));
        }

        private void RecordSnapshot(ObservationSession session, string reason)
        {
            var snapshot = SnapshotCharacter(session);
            _store.TryEnqueue(
                @"INSERT INTO observation_snapshots(
snapshot_id,session_id,captured_utc,reason,snapshot_json)
VALUES($id,$session,$captured,$reason,$snapshot)",
                ("$id", Guid.NewGuid().ToString("N")),
                ("$session", session.SessionId),
                ("$captured", UtcNow()),
                ("$reason", NormalizeText(reason, 120, "snapshot")),
                ("$snapshot", snapshot));
        }

        private static string SnapshotCharacter(ObservationSession session)
        {
            var character = session.Character;
            var quests = character.Quests.Quests.Values
                .OrderBy(q => q.TemplateId)
                .Select(q => new
                {
                    quest_id = q.TemplateId,
                    component_id = q.ComponentId,
                    step = (int)q.Step,
                    status = (int)q.Status,
                    objectives = q.Objectives?.ToArray() ?? Array.Empty<int>()
                })
                .ToArray();
            var completed = character.Quests.CompletedQuests.Values
                .OrderBy(q => q.Id)
                .Select(q =>
                {
                    var bytes = new byte[8];
                    q.Body?.CopyTo(bytes, 0);
                    return new { block_id = q.Id, body_base64 = Convert.ToBase64String(bytes) };
                })
                .ToArray();
            var items = session.TouchedItemIds.Keys
                .OrderBy(id => id)
                .Select(id => new
                {
                    item_id = id,
                    count = character.Inventory.GetItemsCount(id)
                })
                .ToArray();
            return JsonConvert.SerializeObject(
                new { quests, completed, items },
                Formatting.None);
        }

        private static void RestoreTouchedItems(
            ObservationSession session,
            string snapshotJson)
        {
            try
            {
                var root = JObject.Parse(snapshotJson);
                foreach (var item in root["items"] ?? new JArray())
                {
                    var itemId = item.Value<uint?>("item_id") ?? 0;
                    if (itemId > 0)
                        session.TouchedItemIds.TryAdd(itemId, true);
                }
            }
            catch (JsonException)
            {
                // The mismatch will be recorded by resume_compare.
            }
        }

        private void TouchItems(Character character, string itemIdsJson)
        {
            try
            {
                foreach (var token in JArray.Parse(itemIdsJson ?? "[]"))
                    TouchItem(character, token.Value<uint>());
            }
            catch (JsonException)
            {
                // Catalog JSON is preserved in the event for offline diagnosis.
            }
        }

        private bool TryGetSession(
            Character character,
            out ObservationSession session)
        {
            session = null;
            return Available &&
                   character != null &&
                   _sessions.TryGetValue(character.Id, out session);
        }

        private static string ComputeFileSha256(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var sha = SHA256.Create())
                return ToHex(sha.ComputeHash(stream));
        }

        private static string ComputeSha256(byte[] bytes)
        {
            using (var sha = SHA256.Create())
                return ToHex(sha.ComputeHash(bytes));
        }

        private static string ToHex(byte[] bytes)
        {
            return BitConverter.ToString(bytes).Replace("-", string.Empty);
        }

        private static string UtcNow()
        {
            return DateTime.UtcNow.ToString("O");
        }

        private static object NullIfEmpty(string value)
        {
            return string.IsNullOrEmpty(value) ? (object)DBNull.Value : value;
        }

        private static string NormalizeText(
            string value,
            int maxLength,
            string fallback)
        {
            value = string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
            return value.Length <= maxLength ? value : value.Substring(0, maxLength);
        }

        private sealed class ObservationSession
        {
            public string SessionId { get; set; }
            public string ParentSessionId { get; set; }
            public string Label { get; set; }
            public Character Character { get; set; }
            public long InteractionSequence;
            public long EventSequence;
            public long DroppedAtStart;
            public AA8ObservationGate Gate { get; } = new AA8ObservationGate();
            public ConcurrentDictionary<uint, bool> TouchedItemIds { get; } =
                new ConcurrentDictionary<uint, bool>();
        }

        private sealed class ObservationContext
        {
            public uint CharacterId { get; set; }
            public string SessionId { get; set; }
            public string InteractionId { get; set; }
        }

        private sealed class PendingPacket
        {
            public string Direction { get; set; }
            public uint Opcode { get; set; }
            public byte Level { get; set; }
            public byte[] Bytes { get; set; }
            public bool Persisted { get; set; }
        }

        private sealed class DelegateDisposable : IDisposable
        {
            private Action _dispose;
            public DelegateDisposable(Action dispose) => _dispose = dispose;
            public void Dispose() => Interlocked.Exchange(ref _dispose, null)?.Invoke();
        }

        private sealed class EmptyDisposable : IDisposable
        {
            public static readonly EmptyDisposable Instance = new EmptyDisposable();
            public void Dispose()
            {
            }
        }
    }

    public sealed class AA8ObservationInteraction : IDisposable
    {
        private readonly Action<string> _complete;
        private string _outcome = "recorded";
        private bool _disposed;

        internal static readonly AA8ObservationInteraction NoopAllowed =
            new AA8ObservationInteraction(true, string.Empty, true, null);

        public bool Allowed { get; }
        public string InteractionId { get; }
        public bool IsNoop { get; }

        internal AA8ObservationInteraction(
            bool allowed,
            string interactionId,
            bool isNoop,
            Action<string> complete)
        {
            Allowed = allowed;
            InteractionId = interactionId;
            IsNoop = isNoop;
            _complete = complete;
        }

        internal static AA8ObservationInteraction Nested(string interactionId)
        {
            return new AA8ObservationInteraction(true, interactionId, true, null);
        }

        internal static AA8ObservationInteraction Blocked(string interactionId)
        {
            return new AA8ObservationInteraction(false, interactionId, true, null);
        }

        public void SetOutcome(string outcome)
        {
            if (!string.IsNullOrWhiteSpace(outcome))
                _outcome = outcome;
        }

        public void Dispose()
        {
            if (_disposed)
                return;
            _disposed = true;
            _complete?.Invoke(_outcome);
        }
    }
}
