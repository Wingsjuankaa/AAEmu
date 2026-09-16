using System.Globalization;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Json;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class NuiaSidequestPlacementTests
{
    private const string Catalog = "doodad_spawns_aa10_nuia_sidequests_r575.json";

    [Test]
    public async Task RegionalOverlay_PreservesNativeTransformPhaseAndScale_WithoutPlantableHorseActors()
    {
        var repo = Repo();
        var data = Path.Combine(repo, "AAEmu.Game", "Data", "Worlds", "main_world");
        var json = await File.ReadAllTextAsync(Path.Combine(data, Catalog));
        var rows = JArray.Parse(json);
        var fixture = (await File.ReadAllLinesAsync(Path.Combine(repo, "AAEmu.UnitTests", "Fixtures",
            "nuia_sidequests_r575_placements.csv"))).Skip(1).Select(s => s.Split(',')).ToArray();
        await Assert.That(rows.Count).IsEqualTo(581);
        await Assert.That(fixture.Length).IsEqualTo(rows.Count);
        await Assert.That(rows.Select(r => r.Value<uint>("UnitId")).Distinct().Count()).IsEqualTo(91);
        await Assert.That(rows.Any(r => r.Value<uint>("UnitId") is 4594 or 4725 or 4727 or 4743)).IsFalse();
        var matched = new HashSet<int>();
        foreach (var native in fixture)
        {
            var id = uint.Parse(native[0], CultureInfo.InvariantCulture);
            var selected = rows.Select((row, index) => (row, index)).Where(p => p.row.Value<uint>("UnitId") == id &&
                new[] { "X", "Y", "Z" }.Select((axis, i) =>
                    Math.Abs(p.row["Position"]!.Value<double>(axis) - Number(native[i + 1])) < 0.001).All(b => b)).ToArray();
            await Assert.That(selected.Length).IsEqualTo(1);
            await Assert.That(matched.Add(selected[0].index)).IsTrue();
            var row = selected[0].row;
            foreach (var (axis, i) in new[] { ("Roll", 4), ("Pitch", 5), ("Yaw", 6) })
                await Assert.That(Math.Abs(row["Position"]!.Value<double>(axis) - Number(native[i]))).IsLessThan(0.001);
            await Assert.That(row.Value<double>("Scale")).IsEqualTo(Number(native[7]));
            await Assert.That(row.Value<uint>("FuncGroupId")).IsEqualTo(uint.Parse(native[8], CultureInfo.InvariantCulture));
        }
        var spawners = JsonConvert.DeserializeObject<List<DoodadSpawner>>(json)!;
        await Assert.That(spawners.Select(s => s.InitialFuncGroupId))
            .IsEquivalentTo(rows.Select(r => r.Value<uint>("FuncGroupId")));
    }

    [Test]
    public async Task BoatCluster_ReplacesExactlyTheFiveLegacyBoats_AndKeepsTheirNativeStartPhase()
    {
        var data = Path.Combine(Repo(), "AAEmu.Game", "Data", "Worlds", "main_world");
        var rules = JsonConvert.DeserializeObject<List<JsonDoodadSpawnReplacement>>(
            await File.ReadAllTextAsync(Path.Combine(data, "doodad_spawn_replacements.json")))!;
        var rule = rules.Single(r => r.ReplacementFile == Catalog);
        var old = JsonConvert.DeserializeObject<List<DoodadSpawner>>(
            await File.ReadAllTextAsync(Path.Combine(data, rule.SourceFile)))!;
        var suppressed = old.Where(s => rule.Contains(s.Position)).ToArray();
        await Assert.That(suppressed.Length).IsEqualTo(5);
        await Assert.That(suppressed.All(s => s.UnitId == 2853)).IsTrue();
        var overlay = JsonConvert.DeserializeObject<List<DoodadSpawner>>(
            await File.ReadAllTextAsync(Path.Combine(data, Catalog)))!;
        var boats = overlay.Where(s => s.UnitId == 2853).ToArray();
        await Assert.That(boats.Length).IsEqualTo(5);
        await Assert.That(boats.All(s => rule.Contains(s.Position) && s.InitialFuncGroupId == 6378 && s.Scale == 1f)).IsTrue();
        await Assert.That(boats.All(s => Math.Abs(s.Position.Roll - 53f) < 0.001f)).IsTrue();
    }

    private static double Number(string text) => double.Parse(text, CultureInfo.InvariantCulture);
    private static string Repo()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory != null && !File.Exists(Path.Combine(directory.FullName, "AAEmu.slnx")))
            directory = directory.Parent;
        return directory!.FullName;
    }
}
