using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsTraceAnalysis
    {
        public string TracePath { get; set; }
        public int EventCount { get; set; }
        public int PlaintextPacketCount { get; set; }
        public int WirePacketCount { get; set; }
        public int CounterAnomalyCount { get; set; }
        public List<string> CounterAnomalies { get; set; } = new List<string>();
        public List<string> PacketSequence { get; set; } = new List<string>();
        public int DisconnectCount { get; set; }
        public long? DeathElapsedMs { get; set; }
        public long? DisconnectElapsedMs { get; set; }
        public long? MillisecondsDeathToDisconnect =>
            DeathElapsedMs.HasValue && DisconnectElapsedMs.HasValue
                ? DisconnectElapsedMs.Value - DeathElapsedMs.Value
                : (long?)null;
    }

    public static class MechanicsTraceTools
    {
        public static MechanicsTraceAnalysis Analyze(string tracePath)
        {
            var analysis = new MechanicsTraceAnalysis {TracePath = Path.GetFullPath(tracePath)};
            var counters = new List<(long seq, byte counter, string packet)>();
            foreach (var line in File.ReadLines(tracePath))
            {
                if (string.IsNullOrWhiteSpace(line))
                    continue;
                var item = JObject.Parse(line);
                analysis.EventCount++;
                var kind = (string)item["kind"];
                var packet = ShortPacketName((string)item["packetType"]);
                var elapsed = (long?)item["elapsedMs"];
                if (kind == "plaintext_out")
                {
                    analysis.PlaintextPacketCount++;
                    if (packet != null)
                        analysis.PacketSequence.Add(packet);
                    if ((int?)item["level"] == 5 && item["messageCounter"]?.Type == JTokenType.Integer)
                        counters.Add(((long)item["seq"], (byte)item["messageCounter"], packet));
                    if (packet == "SCUnitDeathPacket" && !analysis.DeathElapsedMs.HasValue)
                        analysis.DeathElapsedMs = elapsed;
                }
                else if (kind == "wire_out")
                {
                    analysis.WirePacketCount++;
                }
                else if (kind == "disconnect")
                {
                    analysis.DisconnectCount++;
                    if (!analysis.DisconnectElapsedMs.HasValue)
                        analysis.DisconnectElapsedMs = elapsed;
                }
            }

            for (var index = 1; index < counters.Count; index++)
            {
                var expected = unchecked((byte)(counters[index - 1].counter + 1));
                if (counters[index].counter == expected)
                    continue;
                analysis.CounterAnomalyCount++;
                analysis.CounterAnomalies.Add(
                    $"seq {counters[index - 1].seq}->{counters[index].seq}: " +
                    $"{counters[index - 1].counter}->{counters[index].counter}, expected {expected}");
            }
            return analysis;
        }

        public static MechanicsScenario Import(
            string tracePath,
            string fixturePath)
        {
            var fixture = JsonConvert.DeserializeObject<MechanicsScenario>(File.ReadAllText(fixturePath)) ??
                          throw new InvalidOperationException("Fixture is not a valid mechanics scenario");
            var analysis = Analyze(tracePath);
            var firstCounter = File.ReadLines(tracePath)
                .Where(line => !string.IsNullOrWhiteSpace(line))
                .Select(JObject.Parse)
                .FirstOrDefault(item =>
                    (string)item["kind"] == "plaintext_out" &&
                    (int?)item["level"] == 5 &&
                    item["messageCounter"]?.Type == JTokenType.Integer)?["messageCounter"];
            if (firstCounter != null)
                fixture.Dd05Initial = (byte)firstCounter;

            var deathWindow = analysis.PacketSequence;
            var death = deathWindow.FindIndex(name => name == "SCUnitDeathPacket");
            var damage = death >= 0
                ? deathWindow.FindIndex(death + 1, name => name == "SCUnitDamagedPacket")
                : -1;
            if (death >= 0 && damage >= death)
                fixture.Expected.PacketSequence = deathWindow.Skip(death).Take(damage - death + 1).ToList();
            fixture.Name = $"{fixture.Name}-imported";
            return fixture;
        }

        public static void WriteJson(string path, object value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
            File.WriteAllText(path, JsonConvert.SerializeObject(value, Formatting.Indented));
        }

        private static string ShortPacketName(string fullName) =>
            string.IsNullOrWhiteSpace(fullName) ? null : fullName.Split('.').Last();
    }
}
