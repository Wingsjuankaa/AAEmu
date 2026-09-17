using System.Numerics;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Models;
using AAEmu.Game.Models.Game.Slaves;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class BoatSpawnGeometryTests
{
    // AA10 authoritative slaves[578], model 1834 / ship_models[36].
    private static SlaveTemplate Moby() => new()
    {
        ObbCenter = new Vector3(0, -2.30074f, 2.659173f),
        ObbSize = new Vector3(10.650344f, 27.57489f, 8.816892f)
    };

    private static ShipModelV1 Model() => new() { MassBoxSizeZ = 10, MassCenterZ = -3.3f };

    [Test]
    public async Task MobyDraftUsesNativeHullBottomInsteadOfMassBox()
    {
        var depth = BoatSpawnGeometry.RequiredDepth(Moby(), Model(), 0);
        await Assert.That(MathF.Abs(depth - 1.749273f)).IsLessThan(0.00001f);
        await Assert.That(BoatSpawnGeometry.RequiredDepth(Moby(),
            new ShipModelV1 { MassBoxSizeZ = 100, MassCenterZ = -50 }, 0)).IsEqualTo(depth);
    }

    [Test]
    public async Task StandalonePlantOffsetIsIncludedOnce()
    {
        var normal = BoatSpawnGeometry.RequiredDepth(Moby(), Model(), 0);
        await Assert.That(BoatSpawnGeometry.RequiredDepth(Moby(), Model(), -1.75f))
            .IsEqualTo(normal + 1.75f);
    }

    [Test]
    [Arguments(false)]
    [Arguments(true)]
    public async Task SolzreedLakeDepthAcceptsMobyFromShoreAndWater(bool swimming)
    {
        // Observed surface 112.9 and lakebed 103.3 were rejected by the old 14.3 m gate.
        var boat = Moby();
        var depth = BoatSpawnGeometry.RequiredDepth(boat, Model(), 0);
        var footprint = BoatSpawnGeometry.Footprint(boat, MathF.PI / 2);
        (float Floor, float Surface) Sample(Vector3 p) => (p.Y < 10 ? 113.7f : 103.3f, 112.9f);
        var caster = swimming ? new Vector3(0, 20, 112) : new Vector3(0, 0, 114);
        var previous = SlaveManager.FindBoatSpawnPosition(caster, 0, 15, 55, 14.3f, Sample);
        var fixedPosition = SlaveManager.FindBoatSpawnPosition(caster, 0, 15, 55, depth, Sample,
            p => BoatSpawnGeometry.ClearsTerrain(p, depth, footprint, Sample));
        await Assert.That(previous.HasValue).IsFalse();
        await Assert.That(fixedPosition.HasValue).IsTrue();
        await Assert.That(fixedPosition!.Value.Z).IsEqualTo(112.9f);
    }

    [Test]
    [Arguments(112f)]
    [Arguments(113.7f)]
    [Arguments(float.NaN)]
    [Arguments(0f)]
    public async Task ShallowDryOrMissingTerrainStillRejects(float floor)
    {
        var boat = Moby();
        await Assert.That(BoatSpawnGeometry.ClearsTerrain(new Vector3(0, 0, 112.9f),
            BoatSpawnGeometry.RequiredDepth(boat, Model(), 0),
            BoatSpawnGeometry.Footprint(boat, 0), _ => (floor, 112.9f))).IsFalse();
    }

    [Test]
    public async Task DeepCenterCannotHideBankUnderStern()
    {
        var boat = Moby();
        var footprint = BoatSpawnGeometry.Footprint(boat, 0);
        await Assert.That(BoatSpawnGeometry.ClearsTerrain(new Vector3(0, 0, 112.9f),
            BoatSpawnGeometry.RequiredDepth(boat, Model(), 0), footprint,
            p => (p.Y < -15 ? 114f : 103f, 112.9f))).IsFalse();
    }

    [Test]
    public async Task FootprintUsesFinalBoatYawAndOffset()
    {
        var boat = Moby();
        var position = new Vector3(0, 0, 112.9f);
        var depth = BoatSpawnGeometry.RequiredDepth(boat, Model(), 0);
        (float Floor, float Surface) Channel(Vector3 p) => (MathF.Abs(p.X) < 6 ? 103f : 114f, 112.9f);
        await Assert.That(BoatSpawnGeometry.ClearsTerrain(position, depth,
            BoatSpawnGeometry.Footprint(boat, 0), Channel)).IsTrue();
        await Assert.That(BoatSpawnGeometry.ClearsTerrain(position, depth,
            BoatSpawnGeometry.Footprint(boat, MathF.PI / 2), Channel)).IsFalse();
    }

    [Test]
    public async Task SearchContinuesWhenCenterFitsButHullDoesNot()
    {
        var boat = Moby();
        var depth = BoatSpawnGeometry.RequiredDepth(boat, Model(), 0);
        var footprint = BoatSpawnGeometry.Footprint(boat, 0);
        (float Floor, float Surface) Sample(Vector3 p) => (p.Y < 10 ? 114f : 103f, 112.9f);
        var result = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 0, 114), 0, 15, 55,
            depth, Sample, p => BoatSpawnGeometry.ClearsTerrain(p, depth, footprint, Sample));
        await Assert.That(result.HasValue).IsTrue();
        // Stern extends 16.09 m behind the origin, so center Y=25 must be rejected.
        await Assert.That(result!.Value.Y).IsGreaterThan(26f);
    }

    [Test]
    public async Task EmptyNativeBoundsPreserveConservativeFallback()
    {
        var boat = new SlaveTemplate();
        await Assert.That(BoatSpawnGeometry.HasBounds(boat)).IsFalse();
        await Assert.That(BoatSpawnGeometry.RequiredDepth(boat, Model(), 0)).IsEqualTo(14.3f);
        await Assert.That(BoatSpawnGeometry.RequiredDepth(boat, null, 0)).IsEqualTo(5f);
        await Assert.That(BoatSpawnGeometry.Footprint(boat, 0).Length).IsEqualTo(0);
    }
}
