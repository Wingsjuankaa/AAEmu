using System;
using System.Collections.Generic;
using System.IO;

using AAEmu.MechanicsLab;

using Newtonsoft.Json;

namespace AAEmu.MechanicsLab.Cli
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            try
            {
                if (args.Length == 0)
                    return Usage();
                var command = args[0].ToLowerInvariant();
                var options = ParseOptions(args);
                switch (command)
                {
                    case "run":
                        return Run(options);
                    case "analyze-trace":
                        return Analyze(options);
                    case "import-trace":
                        return Import(options);
                    default:
                        return Usage();
                }
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(exception);
                return 2;
            }
        }

        private static int Run(IReadOnlyDictionary<string, string> options)
        {
            var scenarioPath = Required(options, "scenario");
            var compactPath = Required(options, "compact");
            var outputDirectory = Required(options, "output");
            var scenario = JsonConvert.DeserializeObject<MechanicsScenario>(File.ReadAllText(scenarioPath)) ??
                           throw new InvalidOperationException("Scenario JSON is invalid");
            var result = new global::AAEmu.MechanicsLab.MechanicsLab(compactPath).Run(scenario);
            Directory.CreateDirectory(outputDirectory);
            var outputPath = Path.Combine(outputDirectory, $"{scenario.Name}.result.json");
            MechanicsTraceTools.WriteJson(outputPath, result);
            MechanicsTraceTools.WriteJson(
                Path.Combine(outputDirectory, $"{scenario.Name}.packets.json"),
                result.Packets);
            MechanicsTraceTools.WriteJson(
                Path.Combine(outputDirectory, $"{scenario.Name}.tasks.json"),
                result.Tasks);
            Console.WriteLine($"scenario={scenario.Name}");
            Console.WriteLine($"passed={result.Passed}");
            Console.WriteLine($"result_sha256={result.ResultSha256}");
            Console.WriteLine($"output={outputPath}");
            return result.Passed ? 0 : 1;
        }

        private static int Analyze(IReadOnlyDictionary<string, string> options)
        {
            var analysis = MechanicsTraceTools.Analyze(Required(options, "trace"));
            var output = Required(options, "output");
            MechanicsTraceTools.WriteJson(output, analysis);
            Console.WriteLine($"counter_anomalies={analysis.CounterAnomalyCount}");
            Console.WriteLine($"death_to_disconnect_ms={analysis.MillisecondsDeathToDisconnect}");
            return analysis.CounterAnomalyCount == 0 ? 0 : 1;
        }

        private static int Import(IReadOnlyDictionary<string, string> options)
        {
            var scenario = MechanicsTraceTools.Import(
                Required(options, "trace"),
                Required(options, "fixture"));
            var output = Required(options, "output");
            MechanicsTraceTools.WriteJson(output, scenario);
            Console.WriteLine($"output={output}");
            return 0;
        }

        private static Dictionary<string, string> ParseOptions(string[] args)
        {
            var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (var index = 1; index < args.Length; index++)
            {
                if (!args[index].StartsWith("--", StringComparison.Ordinal) || index + 1 >= args.Length)
                    throw new ArgumentException($"Invalid option '{args[index]}'");
                result[args[index].Substring(2)] = args[++index];
            }
            return result;
        }

        private static string Required(IReadOnlyDictionary<string, string> options, string name) =>
            options.TryGetValue(name, out var value) && !string.IsNullOrWhiteSpace(value)
                ? value
                : throw new ArgumentException($"--{name} is required");

        private static int Usage()
        {
            Console.Error.WriteLine("aa8-mechanics run --scenario <json> --compact <sqlite> --output <dir>");
            Console.Error.WriteLine("aa8-mechanics analyze-trace --trace <jsonl> --output <json>");
            Console.Error.WriteLine("aa8-mechanics import-trace --trace <jsonl> --fixture <json> --output <scenario>");
            return 2;
        }
    }
}
