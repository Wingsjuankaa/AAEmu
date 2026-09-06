using System.Numerics;
using System.Reflection;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Spheres;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class QuestItemAreaSphereTests
{
    private static readonly FieldInfo Areas = typeof(SphereQuestManager)
        .GetField("_questAreaSpheres", BindingFlags.Static | BindingFlags.NonPublic)!;
    private static readonly FieldInfo Signs = typeof(SphereQuestManager)
        .GetField("_sphereQuests", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _oldAreas;
    private object _oldSigns;
    private SphereGameData _data;
    // Native zone354 local positions; translation to world space preserves distances.
    private readonly Vector3 _fountain = new(1594.94f, 2329.86f, 875.591f);

    [Before(Test)]
    public void Setup()
    {
        _oldAreas = Areas.GetValue(null);
        _oldSigns = Signs.GetValue(null);
        Areas.SetValue(null, new Dictionary<uint, List<SphereQuest>>
        {
            [354] = [new() { SphereId = 2836, WorldId = "main_world", ZoneId = 354,
                Xyz = _fountain, Radius = 12 }]
        });
        Signs.SetValue(null, new Dictionary<uint, List<SphereQuest>>
        {
            [40198] = [new() { QuestId = 9242, ComponentId = 40198, WorldId = "main_world",
                Xyz = new Vector3(1616.71f, 2335.05f, 875.504f), Radius = 12 }]
        });
        _data = new SphereGameData();
        SetData("_spheres", new Dictionary<uint, Spheres>
        {
            [2836] = new() { Id = 2836, SphereDetailType = "SphereQuest", SphereDetailId = 1637 }
        });
        SetData("_sphereQuests", new Dictionary<uint, SphereQuests>
        {
            [1637] = new() { Id = 1637, QuestId = 9242 }
        });
    }

    [After(Test)]
    public void Cleanup()
    {
        Areas.SetValue(null, _oldAreas);
        Signs.SetValue(null, _oldSigns);
    }

    [Test]
    public async Task ExperimentUsesSharedNativeVolumeDespiteDifferentQuestComponent()
    {
        var result = _data.IsInsideAreaSphere(2836, 1, _fountain + new Vector3(10, 0, 0), 40452, "main_world");
        await Assert.That(result?.SphereId).IsEqualTo(2836u);
        await Assert.That(result?.Radius).IsEqualTo(12f);
    }

    [Test]
    public async Task BoundaryIsIncludedButOutsideAndAboveAreRejected()
    {
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, _fountain + new Vector3(12, 0, 0), 40452, "main_world")).IsNotNull();
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, _fountain + new Vector3(12.1f, 0, 0), 40452, "main_world")).IsNull();
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, _fountain + new Vector3(0, 0, 12.1f), 40452, "main_world")).IsNull();
    }

    [Test]
    public async Task ReportNpcMarkerCannotAuthorizeItemOutsideNativeArea()
    {
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, new Vector3(1616.71f, 2335.05f, 875.504f), 40198, "main_world")).IsNull();
    }

    [Test]
    public async Task OtherWorldAndUnknownSphereAreRejected()
    {
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, _fountain, 40452, "instance_world")).IsNull();
        await Assert.That(_data.IsInsideAreaSphere(99999, 1, _fountain, 40452, "main_world")).IsNull();
    }

    [Test]
    public async Task MissingNativeGeometryRetainsLegacyComponentFilter()
    {
        Areas.SetValue(null, new Dictionary<uint, List<SphereQuest>>());
        var report = new Vector3(1616.71f, 2335.05f, 875.504f);
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, report, 40198, "main_world")).IsNotNull();
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, report, 40452, "main_world")).IsNull();
        await Assert.That(_data.IsInsideAreaSphere(2836, 1, report, 40198, "instance_world")).IsNull();
    }

    private void SetData(string name, object value) => typeof(SphereGameData)
        .GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(_data, value);
}
