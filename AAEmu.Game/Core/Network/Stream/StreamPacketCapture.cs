using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Network.Game;
using Newtonsoft.Json;
using NLog;

namespace AAEmu.Game.Core.Network.Stream
{
    /// <summary>
    /// Exact AA8 capture for the independent 2250 stream channel.  A client
    /// protocol abort often closes this socket before the game socket, so it
    /// must be traced separately and correlated through the game-session id.
    /// </summary>
    public sealed class StreamPacketCapture : IDisposable
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

        private readonly object _writeLock = new object();
        private readonly StreamConnection _connection;
        private readonly Stopwatch _clock = Stopwatch.StartNew();
        private readonly StreamWriter _writer;
        private readonly int _maxCapturedBytes;
        private long _sequence;
        private bool _disposed;

        public bool Enabled => _writer != null;
        public string FilePath { get; }

        public StreamPacketCapture(StreamConnection connection)
        {
            _connection = connection;
            if (!ReadBooleanEnvironment("AAEMU_PACKET_CAPTURE_ENABLED", false))
                return;

            _maxCapturedBytes = ReadIntegerEnvironment(
                "AAEMU_PACKET_CAPTURE_MAX_BYTES", 131072, 256, 1048576);
            var directory = Environment.GetEnvironmentVariable("AAEMU_PACKET_CAPTURE_PATH");
            if (string.IsNullOrWhiteSpace(directory))
                directory = Path.Combine(AppContext.BaseDirectory, "runtime-captures", "packet-traces");
            Directory.CreateDirectory(directory);
            FilePath = Path.Combine(directory, string.Format(
                CultureInfo.InvariantCulture,
                "aa8-stream-{0:yyyyMMdd-HHmmssfff}-session-{1}.jsonl",
                DateTime.UtcNow,
                connection.Id));
            _writer = new StreamWriter(
                new FileStream(FilePath, FileMode.CreateNew, FileAccess.Write, FileShare.Read),
                System.Text.Encoding.UTF8)
            {
                AutoFlush = true
            };
            WriteEvent("capture_started", null, null, null, null,
                "Exact AA8 stream-channel capture enabled.");
            Log.Info("[AA8StreamCapture] session={0} path={1}", connection.Id, FilePath);
        }

        public void RecordLinkedGameSession()
        {
            WriteEvent("linked_game_session", null, null, null, null,
                "gameSessionId=" + _connection.GameConnection?.Id);
        }

        public void RecordOutgoing(StreamPacket packet, byte[] bytes)
        {
            WriteEvent(
                "wire_out",
                null,
                packet.TypeId,
                packet.GetType().FullName,
                bytes,
                SafeVerbose(packet));
        }

        public void RecordRawOutgoing(byte[] bytes)
        {
            WriteEvent("wire_out_untyped", null, null, null, bytes, null);
        }

        public void RecordRawIncoming(byte[] bytes)
        {
            WriteEvent("wire_in", null, null, null, bytes, null);
        }

        public void RecordDecodedIncoming(ushort opcode, Type packetType, byte[] bytes)
        {
            WriteEvent(
                "decoded_in",
                null,
                opcode,
                packetType?.FullName,
                bytes,
                packetType == null ? "unregistered opcode" : null);
        }

        public void RecordFailure(string stage, Exception exception)
        {
            WriteEvent("failure", null, null, exception?.GetType().FullName, null,
                stage + ": " + exception);
            GamePacketCapture.RecordGlobalFailure(stage, exception);
        }

        public void RecordDisconnect(string reason)
        {
            WriteEvent("disconnect", null, null, null, null, reason);
        }

        private void WriteEvent(
            string kind,
            byte? level,
            ushort? opcode,
            string packetType,
            byte[] bytes,
            string details)
        {
            if (!Enabled || _disposed)
                return;

            try
            {
                var capturedLength = bytes == null ? 0 : Math.Min(bytes.Length, _maxCapturedBytes);
                var game = _connection.GameConnection;
                var activeChar = game?.ActiveChar;
                var value = new Dictionary<string, object>
                {
                    ["seq"] = Interlocked.Increment(ref _sequence),
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["elapsedMs"] = _clock.ElapsedMilliseconds,
                    ["kind"] = kind,
                    ["thread"] = Thread.CurrentThread.ManagedThreadId,
                    ["streamSessionId"] = _connection.Id,
                    ["gameSessionId"] = game?.Id,
                    ["accountId"] = game?.AccountId,
                    ["characterId"] = activeChar?.Id,
                    ["characterObjId"] = activeChar?.ObjId,
                    ["characterName"] = activeChar?.Name,
                    ["level"] = level,
                    ["opcode"] = opcode,
                    ["opcodeHex"] = opcode.HasValue
                        ? "0x" + opcode.Value.ToString("X3", CultureInfo.InvariantCulture)
                        : null,
                    ["packetType"] = packetType,
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
                Log.Error(exception, "[AA8StreamCapture] Failed to record event {0}", kind);
            }
        }

        private static string SafeVerbose(StreamPacket packet)
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
