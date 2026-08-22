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
        [14134] = 41592,
        [14237] = 41846,
        [14239] = 41856,
        [14240] = 41859,
        [14241] = 41861,
        [14242] = 41863,
        [14243] = 41865,
        [14244] = 41867,
        [14245] = 41869,
        [14246] = 41871,
        [14309] = 41989
    };

    private static readonly IReadOnlyDictionary<uint, (float X, float Y, float Z)> ExpectedPostChapterSevenPositions =
        new Dictionary<uint, (float X, float Y, float Z)>
        {
            [14237] = (7804f, 10336f, 262f),
            [14239] = (7984.048f, 9041.542f, 193.584f),
            [14240] = (8916f, 8171f, 154f),
            [14241] = (8905.84f, 8289.1738f, 154.502f),
            [14242] = (10999f, 9500f, 166f),
            [14243] = (26858.542f, 9038.822f, 773.438f),
            [14244] = (23865f, 7174f, 373.997f),
            [14245] = (9724.452f, 17200.412f, 128.562f),
            [14246] = (9694.577f, 17362.141f, 137.889f),
            [14309] = (29944.83f, 8734.583f, 522.027f)
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

        foreach (var (unitId, expected) in ExpectedPostChapterSevenPositions)
        {
            var position = rows.Single(row => row.Value<uint>("UnitId") == unitId)["Position"]!;
            await Assert.That(Math.Abs(position.Value<float>("X") - expected.X)).IsLessThan(0.001f);
            await Assert.That(Math.Abs(position.Value<float>("Y") - expected.Y)).IsLessThan(0.001f);
            await Assert.That(Math.Abs(position.Value<float>("Z") - expected.Z)).IsLessThan(0.001f);
        }

        var spawners = JsonConvert.DeserializeObject<List<DoodadSpawner>>(json)!;
        var deserialized = spawners.ToDictionary(spawner => spawner.UnitId, spawner => spawner.InitialFuncGroupId);
        await Assert.That(deserialized).IsEquivalentTo(ExpectedPhases);
    }
}
