using System.Reflection;
using AAEmu.Game;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.StaticValues;
using Portal = AAEmu.Game.Models.Game.Portal;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class TeleportBookDiscoveryTests
{
    [Test]
    public async Task NativeDistrictEvent_UsesGroup22AndValue1_NotClientSubZone()
    {
        await Assert.That(ZoneQuestAreaBridge.TryGetBookDistrict(22, 473, out var district)).IsTrue();
        await Assert.That(district).IsEqualTo(473u);
        foreach (var group in new uint[] { 0, 16, 18, 19, 20, 21, 473, 1267 })
            await Assert.That(ZoneQuestAreaBridge.TryGetBookDistrict(group, 473, out _)).IsFalse();
        foreach (var invalid in new[] { 0, -1, int.MaxValue })
            await Assert.That(ZoneQuestAreaBridge.TryGetBookDistrict(22, invalid, out _)).IsFalse();
    }

    [Test]
    public async Task VisitKeys_AreDisjointAndFitExistingSignedSqlInt()
    {
        var district = PortalVisitKey.ForDistrict(473);
        var subzone = PortalVisitKey.ForSubZone(473);
        await Assert.That(district).IsNotEqualTo(subzone);
        await Assert.That(district).IsLessThan((uint)int.MaxValue);
        await Assert.That(PortalVisitKey.DistrictId(district)).IsEqualTo(473u);
        await Assert.That(PortalVisitKey.SubZoneId(subzone)).IsEqualTo(473u);
        await Assert.That(PortalVisitKey.IsDistrict(473)).IsFalse();
        await Assert.That(PortalVisitKey.IsDistrict(subzone)).IsFalse();
    }

    [Test]
    public async Task HiramWithoutClientSubzone_IsAvailableAndRegistersOnce()
    {
        var manager = CreateManager();
        var book = CreateBook(manager);
        await Assert.That(manager.GetRecallBySubZoneId(473)).IsNull();
        await Assert.That(manager.GetRecallById(933).Name).IsEqualTo("Hiram Cave");
        await Assert.That(book.RecordNativeDistrict(473, 1)).IsTrue();
        await Assert.That(book.RecordNativeDistrict(473, 2)).IsFalse();
        await Assert.That(book.DistrictPortals.Count).IsEqualTo(1);
        var entry = book.DistrictPortals[473];
        await Assert.That(entry.Id).IsEqualTo(473u);
        await Assert.That(entry.Type).IsEqualTo(933u);
        await Assert.That(entry.X).IsEqualTo(20075.62f);
        await Assert.That(entry.SubZoneId).IsEqualTo(PortalVisitKey.ForDistrict(473));
    }

    [Test]
    public async Task Collision_DistrictAndPhysicalSubzoneNeverShareNewVisits()
    {
        var manager = CreateManager();
        var physical = new Portal { Id = 999, SubZoneId = 473 };
        Field(manager, "_recalls", new Dictionary<uint, List<Portal>> { [473] = [physical] });
        await Assert.That(manager.GetRecallBySubZoneId(473).Single().Id).IsEqualTo(999u);
        await Assert.That(manager.GetRecallByVisitKey(PortalVisitKey.ForSubZone(473)).Single().Id).IsEqualTo(999u);
        await Assert.That(manager.GetRecallByVisitKey(PortalVisitKey.ForDistrict(473)).Single().Id).IsEqualTo(933u);
        // Old untagged saves retain both historical aliases; no silent loss on upgrade.
        await Assert.That(manager.GetRecallByVisitKey(473).Count).IsEqualTo(2);
    }

    [Test]
    public async Task UnknownDistrictUnplacedDestinationAndUnmappedFaction_DoNotRegister()
    {
        var manager = CreateManager();
        await Assert.That(CreateBook(manager).RecordNativeDistrict(9999, 1)).IsFalse();
        await Assert.That(CreateBook(manager).RecordNativeDistrict(503, 1)).IsFalse();
        await Assert.That(CreateBook(manager, FactionsEnum.Hostile).RecordNativeDistrict(473, 1)).IsFalse();
    }

    [Test]
    public async Task MotherFactionFallback_UsesOnlyMappedDestination()
    {
        var book = CreateBook(CreateManager(), FactionsEnum.NuiaAlliance);
        book.Owner.Faction.MotherId = FactionsEnum.Nuian;
        await Assert.That(book.RecordNativeDistrict(473, 1)).IsTrue();
        await Assert.That(book.DistrictPortals[473].Type).IsEqualTo(933u);
    }

    [Test]
    public async Task SavedVisit_RebuildsSameBookOnFreshInstance()
    {
        var manager = CreateManager();
        var original = CreateBook(manager);
        original.RecordNativeDistrict(473, 71);
        var saved = Visits(original).Values.Single();
        var loaded = CreateBook(manager);
        // Same row fields read by Load(MySqlConnection), on an independent character/book.
        Visits(loaded).Add(saved.SubZone, new VisitedDistrict
            { Id = saved.Id, SubZone = saved.SubZone, Owner = saved.Owner });
        typeof(CharacterPortals).GetMethod("PopulateDistrictPortals", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(loaded, null);
        await Assert.That(loaded.DistrictPortals[473].Type).IsEqualTo(933u);
        await Assert.That(loaded.RecordNativeDistrict(473, 72)).IsFalse();
    }

    [Test]
    public async Task ConcurrentAreaNotifications_RecordSingleVisit()
    {
        var book = CreateBook(CreateManager());
        var tasks = Enumerable.Range(1, 30).Select(i => Task.Run(() => book.RecordNativeDistrict(473, (uint)i)));
        var results = await Task.WhenAll(tasks);
        await Assert.That(results.Count(success => success)).IsEqualTo(1);
        await Assert.That(Visits(book).Count).IsEqualTo(1);
    }

    private static CharacterPortals CreateBook(PortalManager manager, FactionsEnum faction = FactionsEnum.Nuian) => new(
        new Character(new UnitCustomModelParams()) { Id = 1007, Name = "Fixture",
            Faction = new SystemFaction { Id = faction, MotherId = faction } }, manager);

    private static Dictionary<uint, VisitedDistrict> Visits(CharacterPortals book) =>
        (Dictionary<uint, VisitedDistrict>)typeof(CharacterPortals)
            .GetProperty("VisitedDistricts", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(book)!;

    private static PortalManager CreateManager()
    {
        var manager = new PortalManager(Mock.Of<ILocalizationManager>().Object, Mock.Of<IWorldManager>().Object,
            Mock.Of<IZoneManager>().Object, Mock.Of<ISubZoneManager>().Object, Mock.Of<INpcManager>().Object,
            Mock.Of<IObjectIdManager>().Object, Mock.Of<ITaskManager>().Object);
        Field(manager, "_recalls", new Dictionary<uint, List<Portal>>());
        Field(manager, "_recallsKey", new Dictionary<uint, uint>());
        Field(manager, "_districtReturnPoints", new Dictionary<uint, DistrictReturnPoints> {
            [1] = new() { DistrictId = 473, ReturnPointId = 933, FactionId = FactionsEnum.Nuian } });
        var point = new Portal { Id = 933, Name = "Hiram Cave", ZoneId = 351,
            X = 20075.62f, Y = 29717, Z = 368.722f };
        Field(manager, "_nativeRecallsById", new Dictionary<uint, Portal> { [933] = point });
        typeof(PortalManager).GetMethod("RegisterBindingDistrictAliases", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(manager, [new Dictionary<uint, Portal> { [933] = point },
                new Dictionary<uint, HashSet<uint>> { [933] = [473] }]);
        return manager;
    }

    private static void Field<T>(PortalManager manager, string name, T value) =>
        typeof(PortalManager).GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(manager, value);
}
