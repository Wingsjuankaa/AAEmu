using System.Numerics;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Models.Game.World;

[NotInParallel]
public class AreaShapeLineTests
{
    private static Unit At(uint id, float x, float y, float z = 0f)
    {
        var unit = new Unit { ObjId = id };
        unit.Transform.Local.SetPosition(x, y, z);
        return unit;
    }

    // r575 skill23592/plot1226/event9896: the native line OBB has half-extents3/25/3.
    private static AreaShape PrecisionShot() => new()
    {
        Id = 4843, Type = AreaShapeType.Line, AreaTargetKind = AreaTargetKindType.PreviousTarget,
        Value1 = 3f, Value2 = 25f, Value3 = 3f
    };

    [Test]
    [Arguments(30f)]
    [Arguments(45f)]
    [Arguments(50f)]
    public async Task FixedLineCoversBothLongitudinalHalfExtents(float distance)
    {
        var target = At(2, 0, distance);
        var hits = PrecisionShot().ComputeCorridor(Vector3.Zero, Vector3.UnitY, [target], distance);
        await Assert.That(hits).Contains(target);
    }

    [Test]
    public async Task FullLengthDoesNotWidenTheSidesHeightOrRear()
    {
        var shape = PrecisionShot();
        var hits = shape.ComputeCorridor(Vector3.Zero, Vector3.UnitY,
            [At(2, 0, 50.1f), At(3, 3.1f, 30), At(4, 0, 30, 3.1f), At(5, 0, -.1f)], 100);
        await Assert.That(hits).IsEmpty();
    }

    [Test]
    public async Task NativeHalfLengthDoesNotDependOnTheChosenAimDistanceOrWorldHeading()
    {
        var target = At(2, 45, 0);
        var outside = At(3, 50.1f, 0);
        var hits = PrecisionShot().ComputeCorridor(Vector3.Zero, new Vector3(3, 0, 0), [target, outside], 10);
        await Assert.That(hits.Count).IsEqualTo(1);
        await Assert.That(hits[0]).IsSameReferenceAs(target);
    }

    [Test]
    public async Task ZeroLengthDescriptorKeepsItsExistingAnchorDistanceFallback()
    {
        var shape = PrecisionShot();
        shape.Value2 = 0;
        var target = At(2, 0, 30);
        var hits = shape.ComputeCorridor(Vector3.Zero, Vector3.UnitY, [target, At(3, 0, 30.1f)], 30);
        await Assert.That(hits.Count).IsEqualTo(1);
        await Assert.That(hits[0]).IsSameReferenceAs(target);
    }

    [Test]
    public async Task WorldCandidateSearchReachesTheFarHalfBeforeTheNarrowGeometryFilter()
    {
        using var scope = TestDungeonWorld.InstallWorldManager();
        const int size = 4;
        var map = new uint[size, size];
        for (var x = 0; x < size; x++)
        for (var y = 0; y < size; y++) map[x, y] = 1;
        var template = new WorldTemplate { Id = 1, Name = "line_test", CellX = 1, CellY = 1,
            ZoneKeys = [1], ZoneKeyByRegions = map };
        using var world = new WorldInstance(template, 0, true, 1);
        world.Regions = new Region[size, size];
        for (var x = 0; x < size; x++)
        for (var y = 0; y < size; y++) world.Regions[x, y] = new Region(world, x, y, 1);
        var caster = At(1, 69, 69);
        var target = At(2, 69, 114);
        caster.Region = world.Regions[1, 1];
        target.Region = world.Regions[1, 1];
        caster.Region.AddObject(caster);
        target.Region.AddObject(target);

        var hits = WorldManager.GetAroundByShape<Unit>(caster, PrecisionShot(), caster, target);

        await Assert.That(hits).Contains(target);
    }
}
