using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Threading;

using AAEmu.Commons.Cryptography;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Mechanics;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsTimelineEvent
    {
        public long Sequence { get; set; }
        public DateTime TimestampUtc { get; set; }
        public string Event { get; set; }
        public uint ActorId { get; set; }
        public uint TargetId { get; set; }
        public string Detail { get; set; }
    }

    public sealed class MechanicsTimeline : IMechanicsEventSink
    {
        private readonly ManualMechanicsClock _clock;
        private long _sequence;
        public List<MechanicsTimelineEvent> Events { get; } = new List<MechanicsTimelineEvent>();

        public MechanicsTimeline(ManualMechanicsClock clock)
        {
            _clock = clock;
        }

        public void Add(string eventName, uint actorId, uint targetId, string detail)
        {
            Events.Add(new MechanicsTimelineEvent
            {
                Sequence = ++_sequence,
                TimestampUtc = _clock.UtcNow,
                Event = eventName,
                ActorId = actorId,
                TargetId = targetId,
                Detail = detail
            });
        }

        public void RecordEvent(string eventName, uint actorId, uint targetId, string detail) =>
            Add(eventName, actorId, targetId, detail);
    }

    public sealed class PacketLedgerEntry
    {
        public long Sequence { get; set; }
        public long? TransportSequence { get; set; }
        public DateTime TimestampUtc { get; set; }
        public string Packet { get; set; }
        public ushort Opcode { get; set; }
        public byte Level { get; set; }
        public byte? Counter { get; set; }
        public string PlaintextBase64 { get; set; }
        public string WireBase64 { get; set; }
        public bool BodyConsumedExactly { get; set; }
        public bool WireMatchesPlaintext { get; set; }
        public uint? RuntimeBuffIndex { get; set; }
        public long? UnitPointsHealth { get; set; }
        public long? UnitPointsMana { get; set; }
    }

    public sealed class RecordingPacketLedger : IMechanicsPacketObserver, IMechanicsPacketTransport
    {
        private readonly ManualMechanicsClock _clock;
        private readonly object _sync = new object();
        private readonly Dictionary<GamePacket, PacketLedgerEntry> _pendingByPacket =
            new Dictionary<GamePacket, PacketLedgerEntry>();
        private long _sequence;
        private long _transportSequence;
        private ManualResetEventSlim _probeSecondArrival;
        private ManualResetEventSlim _probeFirstArrival;
        private int _probeArrivalCount;
        private TimeSpan _probeTimeout;
        public uint SessionId { get; }
        public IPAddress Ip => IPAddress.Loopback;
        public List<PacketLedgerEntry> Entries { get; } = new List<PacketLedgerEntry>();
        public List<byte[]> TransportWrites { get; } = new List<byte[]>();

        public RecordingPacketLedger(ManualMechanicsClock clock, uint sessionId = 0xAA800001)
        {
            _clock = clock;
            SessionId = sessionId;
        }

        public void RecordPlaintext(GamePacket packet, byte counter, byte[] plaintext)
        {
            var body = packet.Write(new PacketStream()).GetBytes();
            var entry = new PacketLedgerEntry
            {
                TimestampUtc = _clock.UtcNow,
                Packet = packet.GetType().Name,
                Opcode = packet.TypeId,
                Level = packet.Level,
                Counter = counter,
                PlaintextBase64 = Convert.ToBase64String(plaintext),
                BodyConsumedExactly = plaintext.Length == 3 + body.Length
            };
            if (packet.GetType().Name == "SCBuffRemovedPacket")
            {
                var field = packet.GetType().GetField("_index", BindingFlags.Instance | BindingFlags.NonPublic);
                if (field?.GetValue(packet) is uint index)
                    entry.RuntimeBuffIndex = index;
            }
            else if (packet.GetType().Name == "SCUnitPointsPacket")
            {
                var healthField = packet.GetType().GetField("_preciseHealth",
                    BindingFlags.Instance | BindingFlags.NonPublic);
                var manaField = packet.GetType().GetField("_preciseMana",
                    BindingFlags.Instance | BindingFlags.NonPublic);
                if (healthField?.GetValue(packet) is long health)
                    entry.UnitPointsHealth = health;
                if (manaField?.GetValue(packet) is long mana)
                    entry.UnitPointsMana = mana;
            }
            lock (_sync)
            {
                entry.Sequence = ++_sequence;
                _pendingByPacket[packet] = entry;
                Entries.Add(entry);
            }
        }

        public void RecordWire(GamePacket packet, byte[] wire)
        {
            PacketLedgerEntry entry;
            lock (_sync)
            {
                if (!_pendingByPacket.TryGetValue(packet, out entry))
                {
                    entry = new PacketLedgerEntry
                    {
                        Sequence = ++_sequence,
                        TimestampUtc = _clock.UtcNow,
                        Packet = packet.GetType().Name,
                        Opcode = packet.TypeId,
                        Level = packet.Level
                    };
                    Entries.Add(entry);
                }
                entry.WireBase64 = Convert.ToBase64String(wire);
                entry.WireMatchesPlaintext = ValidateWire(entry, wire);
                _pendingByPacket.Remove(packet);
            }
        }

        public bool Send(byte[] wire)
        {
            var blockFirstArrival = false;
            lock (_sync)
            {
                if (_probeSecondArrival != null && IsLevelFiveWire(wire))
                {
                    blockFirstArrival = ++_probeArrivalCount == 1;
                    if (blockFirstArrival)
                        _probeFirstArrival.Set();
                }
            }

            // This bounded probe deterministically exposes Encode/Send races: an
            // unlocked second sender overtakes the first; an atomic connection
            // keeps the second outside and the first proceeds after the timeout.
            if (blockFirstArrival)
                _probeSecondArrival.Wait(_probeTimeout);

            lock (_sync)
            {
                var clone = (byte[])wire.Clone();
                TransportWrites.Add(clone);
                var encoded = Convert.ToBase64String(wire);
                var entry = Entries
                    .Where(candidate => candidate.TransportSequence == null && candidate.WireBase64 == encoded)
                    .OrderBy(candidate => candidate.Sequence)
                    .FirstOrDefault();
                if (entry != null)
                    entry.TransportSequence = ++_transportSequence;
                if (_probeSecondArrival != null && _probeArrivalCount == 2 && IsLevelFiveWire(wire))
                    _probeSecondArrival.Set();
            }
            return true;
        }

        private static bool IsLevelFiveWire(byte[] wire) =>
            wire != null &&
            ((wire.Length >= 2 && wire[0] == 0xDD && wire[1] == 5) ||
             (wire.Length >= 4 && wire[2] == 0xDD && wire[3] == 5));

        public void ArmTransportReorderingProbe(TimeSpan? timeout = null)
        {
            lock (_sync)
            {
                _probeSecondArrival?.Dispose();
                _probeFirstArrival?.Dispose();
                _probeSecondArrival = new ManualResetEventSlim(false);
                _probeFirstArrival = new ManualResetEventSlim(false);
                _probeArrivalCount = 0;
                _probeTimeout = timeout ?? TimeSpan.FromMilliseconds(250);
            }
        }

        public bool WaitForProbeFirstArrival(TimeSpan timeout) =>
            _probeFirstArrival?.Wait(timeout) == true;

        public void Clear()
        {
            Entries.Clear();
            TransportWrites.Clear();
            _pendingByPacket.Clear();
            _sequence = 0;
            _transportSequence = 0;
            _probeSecondArrival?.Dispose();
            _probeFirstArrival?.Dispose();
            _probeSecondArrival = null;
            _probeFirstArrival = null;
            _probeArrivalCount = 0;
        }

        private static bool ValidateWire(PacketLedgerEntry entry, byte[] wire)
        {
            if (entry.Level != 5 || wire == null || wire.Length < 4 ||
                string.IsNullOrEmpty(entry.PlaintextBase64))
                return entry.Level != 5;

            // PacketStream prepends the two-byte frame length when a GamePacket is
            // written to the connection.  Captures taken before that framing start
            // directly at DD05, so accept both representations and validate the
            // same encrypted payload.
            var packetOffset = wire[0] == 0xDD && wire[1] == 5
                ? 0
                : wire.Length >= 6 && wire[2] == 0xDD && wire[3] == 5
                    ? 2
                    : -1;
            if (packetOffset < 0)
                return false;
            var encrypted = wire.Skip(packetOffset + 2).ToArray();
            var decoded = EncryptionManager.Instance.StoCEncrypt(encrypted);
            if (decoded.Length < 2)
                return false;
            var plaintext = Convert.FromBase64String(entry.PlaintextBase64);
            return decoded.Skip(1).SequenceEqual(plaintext);
        }
    }
}
