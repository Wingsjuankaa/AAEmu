using AAEmu.Game.Models.Game.DoodadObj;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class NuiaRacialQuestProxyCatalogTests
{
    private static readonly IReadOnlyDictionary<uint, uint> ExpectedPhases = new Dictionary<uint, uint>
    {
        [14073] = 41492,
        [14074] = 41496,
        [14109] = 41537,
        [14114] = 41557,
        [14118] = 41555,
        [14120] = 41562,
        [14121] = 41567,
        [14122] = 41568,
        [14124] = 41574,
        [14125] = 41603,
        [14134] = 41592
    };

    [Test]
    public async Task Catalog_ContainsEveryNuiaClientQuestActorWithExplicitNativePhase()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null &&
               !(repo.Name == "AAEmu" && File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx"))))
            repo = repo.Parent;

        await Assert.That(repo).IsNotNull();
        var path = Path.Combine(repo!.FullName, "AAEmu.Game", "Data", "Worlds", "main_world",
            "doodad_spawns_aa10_client_quest_proxies.json");
        var json = await File.ReadAllTextAsync(path);
        var rows = JArray.Parse(json);

        var actual = rows.ToDictionary(
            row => row.Value<uint>("UnitId"),
            row => row.Value<uint>("FuncGroupId"));

        await Assert.That(actual).IsEquivalentTo(ExpectedPhases);
        await Assert.That(rows.All(row => row.Value<float>("Scale") == 1f)).IsTrue();

        var spawners = JsonConvert.DeserializeObject<List<DoodadSpawner>>(json)!;
        var deserialized = spawners.ToDictionary(spawner => spawner.UnitId, spawner => spawner.InitialFuncGroupId);
        await Assert.That(deserialized).IsEquivalentTo(ExpectedPhases);
    }
}
