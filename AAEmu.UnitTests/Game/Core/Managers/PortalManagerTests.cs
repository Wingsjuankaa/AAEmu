using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using Newtonsoft.Json;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class PortalManagerTests
{
    [Test]
    public async Task Constructor_DoesNotCallDeps()
    {
        var mockLocale = Mock.Of<ILocalizationManager>();
        var mockWorld = Mock.Of<IWorldManager>();
        var mockZone = Mock.Of<IZoneManager>();
        var mockNpc = Mock.Of<INpcManager>();
        var mockObjId = Mock.Of<IObjectIdManager>();
        var mockTask = Mock.Of<ITaskManager>();
        var manager = new PortalManager(mockLocale.Object, mockWorld.Object, mockZone.Object, mockNpc.Object, mockObjId.Object, mockTask.Object);

        await Assert.That(manager).IsNotNull();
        Mock.VerifyNoOtherCalls(mockLocale);
        Mock.VerifyNoOtherCalls(mockWorld);
        Mock.VerifyNoOtherCalls(mockZone);
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

    private static PortalManager CreateManager()
    {
        return new PortalManager(
            Mock.Of<ILocalizationManager>().Object,
            Mock.Of<IWorldManager>().Object,
            Mock.Of<IZoneManager>().Object,
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
}
