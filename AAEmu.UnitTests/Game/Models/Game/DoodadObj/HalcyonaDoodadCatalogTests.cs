using AAEmu.Game.Models.Json;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class HalcyonaDoodadCatalogTests
{
    private const float MinX = 7368.648649f;
    private const float MinY = 9216f;
    private const float MaxX = 12288f;
    private const float MaxY = 12168.648649f;

    [Test]
    public async Task ReplacementCatalog_IsTheClosedRetailR575HalcyonaRegion()
    {
        var worldPath = FindWorldDataPath();
        var replacementPath = Path.Combine(worldPath, "doodad_spawns_aa10_halcyona_r575.json");
        var rows = JArray.Parse(await File.ReadAllTextAsync(replacementPath));

        await Assert.That(rows.Count).IsEqualTo(6600);
        await Assert.That(rows.All(IsInsideHalcyona)).IsTrue();
        await Assert.That(rows.All(row => row.Value<float>("Scale") > 0f)).IsTrue();
        await Assert.That(rows.Count(row => Math.Abs(row.Value<float>("Scale") - 1f) > 0.000001f))
            .IsEqualTo(812);

        var rock = rows.Single(row => row.Value<uint>("UnitId") == 8441);
        var position = rock["Position"]!;
        await Assert.That(position.Value<float>("X")).IsEqualTo(11017.739f);
        await Assert.That(position.Value<float>("Y")).IsEqualTo(10279.9595f);
        await Assert.That(position.Value<float>("Z")).IsEqualTo(243.677f);
        await Assert.That(position.Value<float>("Roll")).IsEqualTo(0f);
        await Assert.That(position.Value<float>("Pitch")).IsEqualTo(0f);
        await Assert.That(position.Value<float>("Yaw")).IsEqualTo(0f);
        await Assert.That(rock.Value<float>("Scale")).IsEqualTo(1f);
    }

    [Test]
    public async Task ReplacementManifest_SuppressesOnlyTheLegacyBaseRegion()
    {
        var worldPath = FindWorldDataPath();
        var manifestPath = Path.Combine(worldPath, "doodad_spawn_replacements.json");
        var replacements = JsonConvert.DeserializeObject<List<JsonDoodadSpawnReplacement>>(
            await File.ReadAllTextAsync(manifestPath))!;

        await Assert.That(replacements.Count).IsEqualTo(1);
        var replacement = replacements[0];
        await Assert.That(replacement.SourceFile).IsEqualTo("doodad_spawns.json");
        await Assert.That(replacement.ReplacementFile).IsEqualTo("doodad_spawns_aa10_halcyona_r575.json");
        await Assert.That(replacement.MinX).IsEqualTo(MinX);
        await Assert.That(replacement.MinY).IsEqualTo(MinY);
        await Assert.That(replacement.MaxX).IsEqualTo(MaxX);
        await Assert.That(replacement.MaxY).IsEqualTo(MaxY);

        var baseRows = JArray.Parse(await File.ReadAllTextAsync(Path.Combine(worldPath, replacement.SourceFile)));
        await Assert.That(baseRows.Count(IsInsideHalcyona)).IsEqualTo(8092);
        await Assert.That(baseRows.Single(row => row.Value<uint>("UnitId") == 8441)
            .Value<float>("Scale")).IsEqualTo(0f);
    }

    private static bool IsInsideHalcyona(JToken row)
    {
        var position = row["Position"]!;
        var x = position.Value<float>("X");
        var y = position.Value<float>("Y");
        return x >= MinX && x < MaxX && y >= MinY && y < MaxY;
    }

    private static string FindWorldDataPath()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null && !(repo.Name == "AAEmu" && File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx"))))
            repo = repo.Parent;

        return Path.Combine(repo!.FullName, "AAEmu.Game", "Data", "Worlds", "main_world");
    }
}
