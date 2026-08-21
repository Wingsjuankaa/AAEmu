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

    private static void SetField<T>(PortalManager manager, string name, T value)
    {
        var field = typeof(PortalManager).GetField(name,
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(manager, value);
    }
}
