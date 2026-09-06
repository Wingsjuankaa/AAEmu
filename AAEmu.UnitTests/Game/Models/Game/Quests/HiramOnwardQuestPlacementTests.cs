using System.Globalization;
using AAEmu.Game.Models.Game.DoodadObj;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class HiramOnwardQuestPlacementTests
{
    [Test]
    public async Task Catalog_PreservesAllNativePlacementsIncludingTiltScaleAndStartPhase()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null && !File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx")))
            repo = repo.Parent;
        await Assert.That(repo).IsNotNull();
        var fixture = Path.Combine(repo!.FullName, "AAEmu.UnitTests", "Fixtures", "hiram_onward_r575_placements.csv");
        var path = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Worlds", "main_world",
            "doodad_spawns_aa10_hiram_onward_r575.json");
        var json = await File.ReadAllTextAsync(path);
        var actors = JArray.Parse(json);
        var native = (await File.ReadAllLinesAsync(fixture)).Skip(1).Select(line => line.Split(',')).ToArray();
        await Assert.That(actors.Count).IsEqualTo(975);
        await Assert.That(native.Length).IsEqualTo(actors.Count);
        var matched = new HashSet<int>();
        foreach (var row in native)
        {
            var id = uint.Parse(row[0], CultureInfo.InvariantCulture);
            var xyz = row.Skip(1).Take(3).Select(v => double.Parse(v, CultureInfo.InvariantCulture)).ToArray();
            var matches = actors.Select((actor, index) => (actor, index)).Where(entry =>
                entry.actor.Value<uint>("UnitId") == id &&
                new[] { "X", "Y", "Z" }.Select((axis, i) =>
                    Math.Abs(entry.actor["Position"]!.Value<double>(axis) - xyz[i]) < 0.001).All(v => v)).ToArray();
            await Assert.That(matches.Length).IsEqualTo(1);
            await Assert.That(matched.Add(matches[0].index)).IsTrue();
            var actor = matches[0].actor;
            foreach (var (axis, column) in new[] { ("Roll", 4), ("Pitch", 5), ("Yaw", 6) })
                await Assert.That(Math.Abs(actor["Position"]!.Value<double>(axis) -
                    double.Parse(row[column], CultureInfo.InvariantCulture))).IsLessThan(0.001);
            await Assert.That(actor.Value<double>("Scale")).IsEqualTo(double.Parse(row[7], CultureInfo.InvariantCulture));
            await Assert.That(actor.Value<uint>("FuncGroupId")).IsEqualTo(uint.Parse(row[8], CultureInfo.InvariantCulture));
        }
        // The loader must retain each explicit Start phase, including NPC proxies whose
        // generic template heuristic would otherwise select a different visible phase.
        var spawners = JsonConvert.DeserializeObject<List<DoodadSpawner>>(json)!;
        await Assert.That(spawners.Select(s => s.InitialFuncGroupId))
            .IsEquivalentTo(actors.Select(a => a.Value<uint>("FuncGroupId")));
        var statues = actors.Where(a => a.Value<uint>("UnitId") == 13319).ToArray();
        await Assert.That(statues.Length).IsEqualTo(21);
        await Assert.That(statues.All(a => a.Value<uint>("FuncGroupId") == 39119)).IsTrue();
    }
}
