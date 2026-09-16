using System.Numerics;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class WorldSphereGeometryTests
{
    private KeyValuePair<string, Lazy<SphereQuestManager.WorldSphereGeometry>>[] _saved;
    private const string Dungeon = "instance_phantom_of_delphinad";

    [Before(Test)]
    public void Setup()
    {
        _saved = SphereQuestManager.WorldGeometry.ToArray();
        SphereQuestManager.WorldGeometry.Clear();
    }

    [After(Test)]
    public void Cleanup()
    {
        SphereQuestManager.WorldGeometry.Clear();
        foreach (var entry in _saved) SphereQuestManager.WorldGeometry[entry.Key] = entry.Value;
    }

    private static SphereQuestManager Manager(string name, uint id = 0) =>
        new(new WorldInstance(new WorldTemplate { Name = name }, 0, true, id));

    private static SphereQuestManager.WorldSphereGeometry Geometry(string world, uint quest, uint component, uint sphere) =>
        new(new() { [component] = [new() { WorldId = world, QuestId = quest, ComponentId = component }] },
            new() { [384] = [new() { WorldId = world, SphereId = sphere, ZoneId = 384,
                Xyz = new Vector3(713.495f, 1075.36f, 289.325f), Radius = 10 }] });

    [Test]
    public async Task DungeonLoadedAfterMainWorldHasItsOwnMarkersAndExecutionVolumes()
    {
        var main = Manager("main_world");
        var dungeon = Manager(Dungeon, 100);
        main.LoadGeometry(() => Geometry("main_world", 9242, 40198, 2836));
        dungeon.LoadGeometry(() => Geometry(Dungeon, 10052, 43720, 3012));
        var position = new Vector3(713.495f, 1075.36f, 289.325f);
        await Assert.That(dungeon.GetQuestSpheres(43720).Single().QuestId).IsEqualTo(10052u);
        await Assert.That(main.GetQuestSpheres(43720)).IsNull();
        await Assert.That(dungeon.GetContainingQuestAreaSpheres(384, position).Single().SphereId).IsEqualTo(3012u);
        await Assert.That(main.GetContainingQuestAreaSpheres(384, position).Single().SphereId).IsEqualTo(2836u);
        await Assert.That(SphereQuestManager.GetAreaSpheres(3012, Dungeon).Count).IsEqualTo(1);
        await Assert.That(SphereQuestManager.GetAreaSpheres(3012, "main_world").Count).IsEqualTo(0);
        await Assert.That(SphereQuestManager.GetSpheresForQuest(10052).Count).IsEqualTo(1);
        await Assert.That(dungeon.GetContainingQuestAreaSpheres(384, position + new Vector3(11, 0, 0)).Count).IsEqualTo(0);
    }

    [Test]
    public async Task ConcurrentDungeonCopiesLoadGeometryOnceWithoutSharingQuestTriggers()
    {
        var copies = Enumerable.Range(100, 8).Select(id => Manager(Dungeon, (uint)id)).ToArray();
        var loads = 0;
        await Task.WhenAll(copies.Select(copy => Task.Run(() => copy.LoadGeometry(() =>
        {
            Interlocked.Increment(ref loads);
            return Geometry(Dungeon, 10052, 43720, 3012);
        }))));
        await Assert.That(loads).IsEqualTo(1);
        await Assert.That(SphereQuestManager.GetSpheresForQuest(10052).Count).IsEqualTo(1);
        await Assert.That(ReferenceEquals(copies[0].GetSphereQuestTriggers(), copies[1].GetSphereQuestTriggers())).IsFalse();
        await Assert.That(copies.All(copy => copy.GetQuestSpheres(43720).Count == 1)).IsTrue();
    }
}
