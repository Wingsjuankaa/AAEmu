using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class PortalManagerTests
{
    [Test]
    public async Task Constructor_DoesNotCallDeps()
    {
        var mockLocale = Mock.Of<ILocalizationManager>();
        var mockWorld = Mock.Of<IWorldManager>();
        var mockZone = Mock.Of<IZoneManager>();
        var mockSubZone = Mock.Of<ISubZoneManager>();
        var mockNpc = Mock.Of<INpcManager>();
        var mockObjId = Mock.Of<IObjectIdManager>();
        var mockTask = Mock.Of<ITaskManager>();
        var manager = new PortalManager(mockLocale.Object, mockWorld.Object, mockZone.Object, mockSubZone.Object,
            mockNpc.Object, mockObjId.Object, mockTask.Object);

        await Assert.That(manager).IsNotNull();
        Mock.VerifyNoOtherCalls(mockLocale);
        Mock.VerifyNoOtherCalls(mockWorld);
        Mock.VerifyNoOtherCalls(mockZone);
        Mock.VerifyNoOtherCalls(mockSubZone);
        Mock.VerifyNoOtherCalls(mockNpc);
        Mock.VerifyNoOtherCalls(mockObjId);
        Mock.VerifyNoOtherCalls(mockTask);
    }

    [Test]
    public async Task GetReturnDestinationById_PrefersWorldgateAndFallsBackToRecall()
    {
        var manager = CreateManager();
        var recall = new Portal { Id = 18, SubZoneId = 338, Name = "Lacton" };
        var worldgate = new Portal { Id = 18, SubZoneId = 900, Name = "Overlapping worldgate" };

        SetField(manager, "_recalls", new Dictionary<uint, List<Portal>> { [338] = [recall] });
        SetField(manager, "_recallsKey", new Dictionary<uint, uint> { [18] = 338 });
        SetField(manager, "_worldGates", new Dictionary<uint, Portal> { [900] = worldgate });
        SetField(manager, "_worldGatesKey", new Dictionary<uint, uint> { [18] = 900 });

        await Assert.That(manager.GetReturnDestinationById(18)).IsEqualTo(worldgate);

        SetField(manager, "_worldGates", new Dictionary<uint, Portal>());
        SetField(manager, "_worldGatesKey", new Dictionary<uint, uint>());

        await Assert.That(manager.GetReturnDestinationById(18)).IsEqualTo(recall);
        await Assert.That(manager.GetReturnDestinationById(999_999)).IsNull();
    }

    [Test]
    public async Task ParseNativeReturnPoints_ReadsR575ReturnPointGrammar()
    {
        const string contents = """
            object
                name ReturnPoint_sunset_town
                pos ( x 2162.3049, y 1080.2307, z 185.57866 )
                zRot -0.0349066
                radius 3
            object
                name ReturnPoint_without_rotation
                pos ( x 10, y 20, z 30 )
                radius 5
            """;

        var points = PortalManager.ParseNativeReturnPoints(206, contents);

        await Assert.That(points).Count().IsEqualTo(2);
        await Assert.That(points[0].ZoneId).IsEqualTo(206u);
        await Assert.That(points[0].EditorName).IsEqualTo("sunset_town");
        await Assert.That(points[0].X).IsEqualTo(2162.3049f);
        await Assert.That(points[0].Y).IsEqualTo(1080.2307f);
        await Assert.That(points[0].Z).IsEqualTo(185.57866f);
        await Assert.That(points[0].ZRotRadians).IsEqualTo(-0.0349066f);
        await Assert.That(points[1].ZRotRadians).IsEqualTo(0f);
    }

    [Test]
    public async Task LactonQuestReturnPoint_IsPresentInRecallCatalogue()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null &&
               !(repo.Name == "AAEmu" && File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx"))))
            repo = repo.Parent;

        await Assert.That(repo).IsNotNull();
        var path = Path.Combine(repo!.FullName, "AAEmu.Game", "Data", "Portal", "recalls.json");
        var portals = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(path))!;
        var lacton = portals.Single(portal => portal.Id == 18);

        await Assert.That(lacton.ZoneId).IsEqualTo(142u);
        await Assert.That(lacton.SubZoneId).IsEqualTo(338u);
        await Assert.That(lacton.X).IsEqualTo(13_594f);
        await Assert.That(lacton.Y).IsEqualTo(14_536f);
        await Assert.That(lacton.Z).IsEqualTo(109f);
    }

    [Test]
    public async Task CinderstoneQuestReturnPoint_IsPresentAtNativeAa10Spawner()
    {
        var repo = FindRepositoryRoot();
        var path = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "worldgates.json");
        var portals = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(path))!;
        var cinderstone = portals.Single(portal => portal.Id == 999);

        await Assert.That(cinderstone.ZoneId).IsEqualTo(148u);
        await Assert.That(cinderstone.X).IsEqualTo(14_359f);
        await Assert.That(cinderstone.Y).IsEqualTo(11_280f);
        await Assert.That(cinderstone.Z).IsEqualTo(175.667f);
        await Assert.That(cinderstone.Yaw).IsEqualTo(160f);
    }

    [Test]
    public async Task DiamondShoresQuestReturnPoint_IsPresentAtNativeAa10Spawner()
    {
        var repo = FindRepositoryRoot();
        var path = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "worldgates.json");
        var portals = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(path))!;
        var diamondShores = portals.Single(portal => portal.Id == 927);

        await Assert.That(diamondShores.ZoneId).IsEqualTo(282u);
        await Assert.That(diamondShores.X).IsEqualTo(18_759.19f);
        await Assert.That(diamondShores.Y).IsEqualTo(27_270.61f);
        await Assert.That(diamondShores.Z).IsEqualTo(199.864f);
        await Assert.That(diamondShores.Yaw).IsEqualTo(15f);
    }

    [Test]
    public async Task AbandonedWarehouseDoodadReturns_ArePresentAtNativeR575Points()
    {
        var repo = FindRepositoryRoot();
        var path = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "worldgates.json");
        var portals = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(path))!;

        var inside = portals.Single(portal => portal.Id == 868);
        await Assert.That(inside.ZoneId).IsEqualTo(310u);
        await Assert.That(inside.X).IsEqualTo(16_491.2f);
        await Assert.That(inside.Y).IsEqualTo(28_105.46f);
        await Assert.That(inside.Z).IsEqualTo(105.597f);

        var outside = portals.Single(portal => portal.Id == 869);
        await Assert.That(outside.ZoneId).IsEqualTo(310u);
        await Assert.That(outside.X).IsEqualTo(16_499.04f);
        await Assert.That(outside.Y).IsEqualTo(28_109.83f);
        await Assert.That(outside.Z).IsEqualTo(105.538f);
    }

    [Test]
    public async Task NuiaSharedStoryItemReturnDestinations_AreCoveredAtNativeAa10Spawners()
    {
        var repo = FindRepositoryRoot();
        var worldgatePath = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "worldgates.json");
        var recallPath = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "recalls.json");
        var destinations = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(worldgatePath))!
            .Concat(JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(recallPath))!)
            .GroupBy(portal => portal.Id)
            .ToDictionary(group => group.Key, group => group.First());

        // Exhaustive AA10 r575 closure for category 131 quests shared by Nuia
        // (race 1) or all races (race 255). Return point 997 belongs only to the
        // alternate Harani/Warborn route and is deliberately outside this set.
        var expected = new Dictionary<uint, (uint ZoneId, float X, float Y, float Z)>
        {
            [999] = (148, 14_359f, 11_280f, 175.667f),
            [927] = (282, 18_759.19f, 27_270.61f, 199.864f),
            [708] = (281, 17_233.918f, 27_511.28f, 141f),
            [998] = (310, 16_482.9f, 28_100.27f, 105.262f),
            [863] = (344, 14_434.69f, 26_684.73f, 134.25f)
        };

        foreach (var (id, point) in expected)
        {
            await Assert.That(destinations.ContainsKey(id)).IsTrue();
            var destination = destinations[id];
            await Assert.That(destination.ZoneId).IsEqualTo(point.ZoneId);
            await Assert.That(destination.SubZoneId).IsEqualTo(id);
            await Assert.That(destination.X).IsEqualTo(point.X);
            await Assert.That(destination.Y).IsEqualTo(point.Y);
            await Assert.That(destination.Z).IsEqualTo(point.Z);
        }
    }

    [Test]
    public async Task SunsetRecall_IsAnchoredToRetailMemoryTomeAndClearOfCommunityWorkbench()
    {
        var repo = FindRepositoryRoot();
        var portalPath = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Portal", "recalls.json");
        var portals = JsonConvert.DeserializeObject<List<Portal>>(await File.ReadAllTextAsync(portalPath))!;
        var sunset = portals.Single(portal => portal.Id == 176);

        var doodadPath = Path.Combine(repo.FullName, "AAEmu.Game", "Data", "Worlds", "main_world",
            "doodad_spawns_aa10_halcyona_r575.json");
        var doodads = JArray.Parse(await File.ReadAllTextAsync(doodadPath));
        var memoryTome = doodads.Single(row => row.Value<uint>("UnitId") == 3591)["Position"]!;
        var communityWorkbench = doodads
            .Where(row => row.Value<uint>("UnitId") == 12151)
            .Select(row => row["Position"]!)
            .Single(position => Distance2D(position, memoryTome) < 30f);

        await Assert.That(sunset.ZoneId).IsEqualTo(206u);
        await Assert.That(sunset.SubZoneId).IsEqualTo(291u);
        await Assert.That(sunset.X).IsEqualTo(9_319.747f);
        await Assert.That(sunset.Y).IsEqualTo(10_329.538f);
        await Assert.That(sunset.Z).IsEqualTo(187.332f);
        await Assert.That(Distance2D(sunset.X, sunset.Y, memoryTome)).IsBetween(2.99f, 3.01f);
        await Assert.That(Distance2D(sunset.X, sunset.Y, communityWorkbench)).IsGreaterThan(10f);
    }

    private static PortalManager CreateManager()
    {
        return new PortalManager(
            Mock.Of<ILocalizationManager>().Object,
            Mock.Of<IWorldManager>().Object,
            Mock.Of<IZoneManager>().Object,
            Mock.Of<ISubZoneManager>().Object,
            Mock.Of<INpcManager>().Object,
            Mock.Of<IObjectIdManager>().Object,
            Mock.Of<ITaskManager>().Object);
    }

    private static DirectoryInfo FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "AAEmu.slnx")))
            directory = directory.Parent;

        return directory
            ?? throw new DirectoryNotFoundException("Could not locate the AAEmu repository root.");
    }

    private static void SetField<T>(PortalManager manager, string name, T value)
    {
        var field = typeof(PortalManager).GetField(name,
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(manager, value);
    }

    private static float Distance2D(float x, float y, JToken position)
    {
        return MathF.Sqrt(MathF.Pow(x - position.Value<float>("X"), 2) +
                          MathF.Pow(y - position.Value<float>("Y"), 2));
    }

    private static float Distance2D(JToken left, JToken right)
    {
        return Distance2D(left.Value<float>("X"), left.Value<float>("Y"), right);
    }
}
