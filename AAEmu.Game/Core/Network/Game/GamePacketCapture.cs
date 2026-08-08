using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using AAEmu.Game.Core.Network.Connections;
using Newtonsoft.Json;
using NLog;

namespace AAEmu.Game.Core.Network.Game
{
    /// <summary>
    /// Persistent, per-session AA8 wire capture.  Unlike the regular packet
    /// logger this records the exact framed bytes and survives a client-side
    /// protocol abort, where no server exception is produced.
    /// </summary>
    public sealed class GamePacketCapture : IDisposable
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private static readonly object GlobalWriteLock = new object();

        private readonly object _writeLock = new object();
        private readonly GameConnection _connection;
        private readonly Stopwatch _clock;
        private readonly StreamWriter _writer;
        private readonly int _maxCapturedBytes;
        private long _sequence;
        private bool _disposed;

        public bool Enabled => _writer != null;
        public string FilePath { get; }

        public GamePacketCapture(GameConnection connection)
        {
            _connection = connection;
            _clock = Stopwatch.StartNew();

            if (!ReadBooleanEnvironment("AAEMU_PACKET_CAPTURE_ENABLED", false))
                return;

            _maxCapturedBytes = ReadIntegerEnvironment(
                "AAEMU_PACKET_CAPTURE_MAX_BYTES", 131072, 256, 1048576);
            var directory = Environment.GetEnvironmentVariable("AAEMU_PACKET_CAPTURE_PATH");
            if (string.IsNullOrWhiteSpace(directory))
                directory = Path.Combine(AppContext.BaseDirectory, "runtime-captures", "packet-traces");

            Directory.CreateDirectory(directory);
            FilePath = Path.Combine(
                directory,
                string.Format(
                    CultureInfo.InvariantCulture,
                    "aa8-game-{0:yyyyMMdd-HHmmssfff}-session-{1}.jsonl",
                    DateTime.UtcNow,
                    connection.Id));
            _writer = new StreamWriter(
                new FileStream(FilePath, FileMode.CreateNew, FileAccess.Write, FileShare.Read),
                System.Text.Encoding.UTF8)
            {
                AutoFlush = true
            };

            WriteEvent("capture_started", null, null, null, null,
                "Exact wire capture enabled; Base64 payload is capped per event, never silently truncated.");
            Log.Info("[AA8PacketCapture] session={0} path={1}", connection.Id, FilePath);
        }

        public void RecordOutgoing(GamePacket packet, byte[] encoded)
        {
            if (!Enabled)
                return;

            var details = SafeVerbose(packet);
            WriteEvent(
                "wire_out",
                packet.Level,
                packet.TypeId,
                packet.GetType().FullName,
                encoded,
                details,
                packet.Level == 5 ? _connection.LastCount : (byte?)null);
        }

        public void RecordOutgoingPlaintext(GamePacket packet, byte counter, byte[] plaintext)
        {
            if (!Enabled)
                return;

            WriteEvent(
                "plaintext_out",
                packet.Level,
                packet.TypeId,
                packet.GetType().FullName,
                plaintext,
                SafeVerbose(packet),
                counter);
        }

        public void RecordRawOutgoing(byte[] encoded)
        {
            WriteEvent("wire_out_untyped", null, null, null, encoded, null);
        }

        public void RecordRawIncoming(byte[] framedBytes)
        {
            WriteEvent("wire_in", null, null, null, framedBytes, null);
        }

        public void RecordDecodedIncoming(
            byte level,
            ushort opcode,
            Type packetType,
            byte[] decodedFrame)
        {
            WriteEvent(
                "decoded_in",
                level,
                opcode,
                packetType?.FullName,
                decodedFrame,
                packetType == null ? "unregistered opcode" : null);
        }

        public void RecordFailure(string stage, Exception exception)
        {
            WriteEvent(
                "failure",
                null,
                null,
                exception?.GetType().FullName,
                null,
                stage + ": " + exception);
            RecordGlobalFailure(stage, exception);
        }

        public void RecordDisconnect(string reason)
        {
            WriteEvent("disconnect", null, null, null, null, reason);
        }

        public static void RecordGlobalFailure(string stage, Exception exception)
        {
            if (!ReadBooleanEnvironment("AAEMU_PACKET_CAPTURE_ENABLED", false))
                return;

            try
            {
                var directory = Environment.GetEnvironmentVariable("AAEMU_PACKET_CAPTURE_PATH");
                if (string.IsNullOrWhiteSpace(directory))
                    directory = Path.Combine(AppContext.BaseDirectory, "runtime-captures", "packet-traces");
                Directory.CreateDirectory(directory);
                var path = Path.Combine(directory, "aa8-global-failures.jsonl");
                var value = new Dictionary<string, object>
                {
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["stage"] = stage,
                    ["thread"] = Thread.CurrentThread.ManagedThreadId,
                    ["exceptionType"] = exception?.GetType().FullName,
                    ["exception"] = exception?.ToString()
                };
                lock (GlobalWriteLock)
                    File.AppendAllText(path, JsonConvert.SerializeObject(value) + Environment.NewLine);
            }
            catch (Exception captureException)
            {
                Log.Error(captureException, "[AA8PacketCapture] Failed to record global failure");
            }
        }

        private void WriteEvent(
            string kind,
            byte? level,
            ushort? opcode,
            string packetType,
            byte[] bytes,
            string details,
            byte? messageCounter = null)
        {
            if (!Enabled || _disposed)
                return;

            try
            {
                var capturedLength = bytes == null ? 0 : Math.Min(bytes.Length, _maxCapturedBytes);
                var activeChar = _connection.ActiveChar;
                var value = new Dictionary<string, object>
                {
                    ["seq"] = Interlocked.Increment(ref _sequence),
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["elapsedMs"] = _clock.ElapsedMilliseconds,
                    ["kind"] = kind,
                    ["thread"] = Thread.CurrentThread.ManagedThreadId,
                    ["sessionId"] = _connection.Id,
                    ["accountId"] = _connection.AccountId,
                    ["characterId"] = activeChar?.Id,
                    ["characterObjId"] = activeChar?.ObjId,
                    ["characterName"] = activeChar?.Name,
                    ["state"] = _connection.State.ToString(),
                    ["level"] = level,
                    ["opcode"] = opcode,
                    ["opcodeHex"] = opcode.HasValue
                        ? "0x" + opcode.Value.ToString("X3", CultureInfo.InvariantCulture)
                        : null,
                    ["packetType"] = packetType,
                    ["messageCounter"] = messageCounter,
                    ["length"] = bytes?.Length,
                    ["capturedLength"] = bytes == null ? (int?)null : capturedLength,
                    ["truncated"] = bytes != null && capturedLength != bytes.Length,
                    ["base64"] = bytes == null
                        ? null
                        : Convert.ToBase64String(bytes, 0, capturedLength),
                    ["details"] = details
                };

                lock (_writeLock)
                {
                    if (!_disposed)
                        _writer.WriteLine(JsonConvert.SerializeObject(value));
                }
            }
            catch (Exception exception)
            {
                Log.Error(exception, "[AA8PacketCapture] Failed to record event {0}", kind);
            }
        }

        private static string SafeVerbose(GamePacket packet)
        {
            try
            {
                return packet.Verbose();
            }
            catch (Exception exception)
            {
                return "Verbose() failed: " + exception;
            }
        }

        private static bool ReadBooleanEnvironment(string name, bool fallback)
        {
            var value = Environment.GetEnvironmentVariable(name);
            if (string.IsNullOrWhiteSpace(value))
                return fallback;
            return value == "1" || value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                   value.Equals("yes", StringComparison.OrdinalIgnoreCase);
        }

        private static int ReadIntegerEnvironment(
            string name,
            int fallback,
            int minimum,
            int maximum)
        {
            if (!int.TryParse(Environment.GetEnvironmentVariable(name), out var value))
                return fallback;
            return Math.Max(minimum, Math.Min(maximum, value));
        }

        public void Dispose()
        {
            lock (_writeLock)
            {
                if (_disposed)
                    return;
                _disposed = true;
                _writer?.Dispose();
            }
        }
    }
}
