using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class ReedwindHajeTowerCatalogTests
{
    private const string CatalogFileName = "doodad_spawns_aa10_reedwind_haje_towers_r575.json";

    private static readonly IReadOnlyDictionary<uint, ExpectedTower> ExpectedTowers =
        new Dictionary<uint, ExpectedTower>
        {
            [14002] = new(19168.844f, 28172.2f, 260.994f, -104.999956f),
            [14003] = new(20006.369f, 28218.34f, 248.934f, 49.99997f),
            [14004] = new(19993.424f, 29103.095f, 257.992f, 155.000062f),
            [14005] = new(19061.07f, 28981.506f, 260.212f, -109.999975f),
            [14006] = new(19525.0198f, 29172.088f, 252.558f, 170.000036f)
        };

    [Test]
    public async Task Catalog_ContainsTheFiveRetailR575HajeTowers()
    {
        var worldPath = FindWorldDataPath();
        var rows = JArray.Parse(await File.ReadAllTextAsync(Path.Combine(worldPath, CatalogFileName)));

        await Assert.That(rows.Count).IsEqualTo(ExpectedTowers.Count);
        await Assert.That(rows.Select(row => row.Value<uint>("UnitId")).Order())
            .IsEquivalentTo(ExpectedTowers.Keys.Order());

        foreach (var row in rows)
        {
            var unitId = row.Value<uint>("UnitId");
            var expected = ExpectedTowers[unitId];
            var position = row["Position"]!;

            await Assert.That(row.Value<uint>("Id")).IsEqualTo(0u);
            await Assert.That(row.Value<uint>("FuncGroupId")).IsEqualTo(0u);
            await Assert.That(row.Value<float>("Scale")).IsEqualTo(1f);
            await Assert.That(position.Value<float>("X")).IsEqualTo(expected.X);
            await Assert.That(position.Value<float>("Y")).IsEqualTo(expected.Y);
            await Assert.That(position.Value<float>("Z")).IsEqualTo(expected.Z);
            await Assert.That(position.Value<float>("Roll")).IsEqualTo(0f);
            await Assert.That(position.Value<float>("Pitch")).IsEqualTo(0f);
            await Assert.That(position.Value<float>("Yaw")).IsEqualTo(expected.Yaw);
        }
    }

    [Test]
    public async Task BaseCatalog_DoesNotDuplicateTheHajeTowerOverlay()
    {
        var worldPath = FindWorldDataPath();
        var baseRows = JArray.Parse(await File.ReadAllTextAsync(Path.Combine(worldPath, "doodad_spawns.json")));
        var duplicateTowerIds = baseRows
            .Select(row => row.Value<uint>("UnitId"))
            .Where(ExpectedTowers.ContainsKey)
            .ToArray();

        await Assert.That(duplicateTowerIds).IsEmpty();
    }

    private static string FindWorldDataPath()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null && !(repo.Name == "AAEmu" && File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx"))))
            repo = repo.Parent;

        return Path.Combine(repo!.FullName, "AAEmu.Game", "Data", "Worlds", "main_world");
    }

    private sealed record ExpectedTower(float X, float Y, float Z, float Yaw);
}
