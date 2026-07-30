using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    /// <summary>
    /// Append-only, single-writer SQLite sink for AA8 runtime observations.
    /// Gameplay threads only use TryAdd and never wait for disk I/O.
    /// </summary>
    public sealed class AA8ObservationStore : IDisposable
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly string _databasePath;
        private readonly int _batchSize;
        private readonly int _flushIntervalMs;
        private readonly BlockingCollection<WriteRequest> _queue;
        private Task _writerTask;
        private long _dropped;
        private bool _started;

        public AA8ObservationStore(
            string databasePath,
            int queueCapacity,
            int batchSize,
            int flushIntervalMs)
        {
            if (string.IsNullOrWhiteSpace(databasePath))
                throw new ArgumentException("Observation database path is required.", nameof(databasePath));

            _databasePath = Path.GetFullPath(databasePath);
            _batchSize = Math.Max(1, batchSize);
            _flushIntervalMs = Math.Max(25, flushIntervalMs);
            _queue = new BlockingCollection<WriteRequest>(
                new ConcurrentQueue<WriteRequest>(),
                Math.Max(1, queueCapacity));
        }

        public string DatabasePath => _databasePath;
        public int QueueDepth => _queue.Count;
        public long DroppedEvents => Interlocked.Read(ref _dropped);

        public void Start()
        {
            if (_started)
                return;

            var directory = Path.GetDirectoryName(_databasePath);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);

            using (var connection = OpenConnection())
                InitializeSchema(connection);

            _started = true;
            _writerTask = Task.Factory.StartNew(
                WriterLoop,
                CancellationToken.None,
                TaskCreationOptions.LongRunning,
                TaskScheduler.Default);
        }

        public bool TryEnqueue(
            string sql,
            params (string Name, object Value)[] parameters)
        {
            if (!_started || _queue.IsAddingCompleted)
                return false;

            var request = new WriteRequest
            {
                Sql = sql,
                Parameters = parameters ?? Array.Empty<(string, object)>()
            };
            if (_queue.TryAdd(request))
                return true;

            var dropped = Interlocked.Increment(ref _dropped);
            if (dropped == 1 || dropped % 100 == 0)
                Log.Error(
                    "[AA8Observation] Queue full; dropped event count={0}",
                    dropped);
            return false;
        }

        public bool Flush(TimeSpan timeout)
        {
            if (!_started)
                return true;

            var barrier = new TaskCompletionSource<bool>(
                TaskCreationOptions.RunContinuationsAsynchronously);
            try
            {
                if (!_queue.TryAdd(
                        new WriteRequest { Barrier = barrier },
                        (int)Math.Max(1, timeout.TotalMilliseconds)))
                    return false;
                return barrier.Task.Wait(timeout) && barrier.Task.Result;
            }
            catch (InvalidOperationException)
            {
                return false;
            }
        }

        public string ReadLatestSnapshot(string sessionId)
        {
            if (string.IsNullOrWhiteSpace(sessionId) || !File.Exists(_databasePath))
                return null;

            Flush(TimeSpan.FromSeconds(5));
            using (var connection = OpenConnection())
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT snapshot_json FROM observation_snapshots " +
                    "WHERE session_id=$session ORDER BY captured_utc DESC LIMIT 1";
                command.Parameters.AddWithValue("$session", sessionId);
                return command.ExecuteScalar() as string;
            }
        }

        public void Stop(TimeSpan timeout)
        {
            if (!_started)
                return;

            Flush(timeout);
            _queue.CompleteAdding();
            if (_writerTask != null && !_writerTask.Wait(timeout))
                Log.Error("[AA8Observation] Writer did not stop within {0}.", timeout);
            _started = false;
        }

        public void Dispose()
        {
            Stop(TimeSpan.FromSeconds(10));
            _queue.Dispose();
        }

        private SqliteConnection OpenConnection()
        {
            var connection = new SqliteConnection($"Data Source={_databasePath}");
            connection.Open();
            using (var pragma = connection.CreateCommand())
            {
                pragma.CommandText =
                    "PRAGMA journal_mode=WAL;" +
                    "PRAGMA synchronous=NORMAL;" +
                    "PRAGMA busy_timeout=5000;" +
                    "PRAGMA foreign_keys=ON;";
                pragma.ExecuteNonQuery();
            }
            return connection;
        }

        private static void InitializeSchema(SqliteConnection connection)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText = @"
CREATE TABLE IF NOT EXISTS schema_info (
    schema_name TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    authority_boundary TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_info(schema_name,schema_version,authority_boundary)
VALUES('AA8_RUNTIME_OBSERVATIONS',1,'observed_runtime_only_not_native_authority');

CREATE TABLE IF NOT EXISTS observation_sessions (
    session_id TEXT PRIMARY KEY,
    parent_session_id TEXT,
    label TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    character_name TEXT NOT NULL,
    race INTEGER NOT NULL,
    level INTEGER NOT NULL,
    network_session_id INTEGER NOT NULL,
    server_build TEXT NOT NULL,
    compact_sha256 TEXT NOT NULL,
    forensic_graph_sha256 TEXT NOT NULL,
    started_utc TEXT NOT NULL,
    ended_utc TEXT,
    end_reason TEXT,
    clean_disconnect INTEGER,
    dropped_events INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS observation_interactions (
    interaction_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    operation TEXT NOT NULL,
    quest_id INTEGER,
    started_utc TEXT NOT NULL,
    ended_utc TEXT,
    outcome TEXT,
    expected_json TEXT,
    actual_json TEXT,
    FOREIGN KEY(session_id) REFERENCES observation_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS observation_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    interaction_id TEXT,
    sequence_no INTEGER NOT NULL,
    captured_utc TEXT NOT NULL,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    operation TEXT NOT NULL,
    quest_id INTEGER,
    component_id INTEGER,
    act_type TEXT,
    detail_id INTEGER,
    dependency_kind TEXT,
    dependency_id INTEGER,
    expected_json TEXT,
    actual_json TEXT,
    blocker_code TEXT,
    exception_summary TEXT,
    FOREIGN KEY(session_id) REFERENCES observation_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS observation_packets (
    packet_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    interaction_id TEXT,
    captured_utc TEXT NOT NULL,
    direction TEXT NOT NULL,
    opcode INTEGER NOT NULL,
    level INTEGER NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    is_unknown INTEGER NOT NULL,
    payload_prefix_hex TEXT,
    FOREIGN KEY(session_id) REFERENCES observation_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS observation_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    captured_utc TEXT NOT NULL,
    reason TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES observation_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS ix_observation_events_family
ON observation_events(act_type,dependency_kind,dependency_id,blocker_code);
CREATE INDEX IF NOT EXISTS ix_observation_events_quest
ON observation_events(quest_id,status);
CREATE INDEX IF NOT EXISTS ix_observation_packets_interaction
ON observation_packets(interaction_id,captured_utc);
";
                command.ExecuteNonQuery();
            }
        }

        private void WriterLoop()
        {
            try
            {
                using (var connection = OpenConnection())
                {
                    while (!_queue.IsCompleted)
                    {
                        if (!_queue.TryTake(out var first, _flushIntervalMs))
                            continue;

                        if (first.Barrier != null)
                        {
                            first.Barrier.TrySetResult(true);
                            continue;
                        }

                        var batch = new List<WriteRequest>(_batchSize) { first };
                        while (batch.Count < _batchSize &&
                               _queue.TryTake(out var next))
                        {
                            if (next.Barrier != null)
                            {
                                WriteBatch(connection, batch);
                                batch.Clear();
                                next.Barrier.TrySetResult(true);
                                break;
                            }
                            batch.Add(next);
                        }

                        if (batch.Count > 0)
                            WriteBatch(connection, batch);
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Fatal(ex, "[AA8Observation] Writer stopped unexpectedly.");
                while (_queue.TryTake(out var pending))
                    pending.Barrier?.TrySetException(ex);
            }
        }

        private static void WriteBatch(
            SqliteConnection connection,
            IReadOnlyCollection<WriteRequest> batch)
        {
            using (var transaction = connection.BeginTransaction())
            {
                foreach (var request in batch)
                {
                    using (var command = connection.CreateCommand())
                    {
                        command.Transaction = transaction;
                        command.CommandText = request.Sql;
                        foreach (var parameter in request.Parameters)
                            command.Parameters.AddWithValue(
                                parameter.Name,
                                parameter.Value ?? DBNull.Value);
                        command.ExecuteNonQuery();
                    }
                }
                transaction.Commit();
            }
        }

        private sealed class WriteRequest
        {
            public string Sql { get; set; }
            public (string Name, object Value)[] Parameters { get; set; }
            public TaskCompletionSource<bool> Barrier { get; set; }
        }
    }
}
