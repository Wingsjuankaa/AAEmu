using System.Numerics;

using AAEmu.Game.Core.Managers;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class BoatSpawnPlacementTests
{
    private static (float Floor, float Surface) CoastalTerrain(Vector3 probe) =>
        (probe.Y < 10f ? 106f : probe.Y < 60f ? 95f : 80f, 100f);

    [Test]
    public async Task DryShoreRetainsWaterReachOfNearbySwimmingPosition()
    {
        // Reproduction: the fishing boat needs 14.3m depth, beyond the old 55m
        // caster radius, but the same water is reachable after walking into the sea.
        var shore = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 0, 106), 0,
            15, 55, 14.3f, CoastalTerrain);
        var swimming = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 12, 99), 0,
            15, 55, 14.3f, CoastalTerrain);
        await Assert.That(shore.HasValue).IsTrue();
        await Assert.That(swimming.HasValue).IsTrue();
        await Assert.That(shore!.Value.Y).IsGreaterThanOrEqualTo(60f);
        await Assert.That(shore.Value.Y).IsLessThanOrEqualTo(70f);
        await Assert.That(shore.Value.Z).IsEqualTo(100f);
    }

    [Test]
    public async Task FacingInlandStillFindsSeaBehindTheCaster()
    {
        var result = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 0, 106), MathF.PI,
            15, 55, 14.3f, CoastalTerrain);
        await Assert.That(result.HasValue).IsTrue();
        await Assert.That(result!.Value.Y).IsGreaterThanOrEqualTo(60f);
    }

    [Test]
    public async Task SwimmingPlacementRetainsTemplateDistanceAndHeading()
    {
        var result = SlaveManager.FindBoatSpawnPosition(new Vector3(100, 100, 99), 0,
            15, 55, 14.3f, _ => (80f, 100f));
        await Assert.That(result).IsEqualTo(new Vector3(100, 115, 100));
    }

    [Test]
    public async Task DistantInlandPositionCannotExtendSearchToRemoteSea()
    {
        var result = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 0, 106), 0,
            15, 55, 14.3f, p => (p.Y < 60f ? 106f : 80f, 100f));
        await Assert.That(result.HasValue).IsFalse();
    }

    [Test]
    [Arguments(106f, 100f)]
    [Arguments(95f, 100f)]
    [Arguments(150f, 200f)]
    [Arguments(float.NaN, 100f)]
    [Arguments(80f, float.NaN)]
    public async Task InvalidTerrainNeverProducesASpawn(float floor, float surface)
    {
        var result = SlaveManager.FindBoatSpawnPosition(new Vector3(0, 0, 106), 0,
            15, 55, 14.3f, _ => (floor, surface));
        await Assert.That(result.HasValue).IsFalse();
    }

    [Test]
    public async Task ForwardDot_AheadIsPositive()
    {
        var caster = new Vector3(0f, 0f, 100f);
        // yaw 0 → forward is +Y
        var ahead = new Vector3(0f, 10f, 100f);
        await Assert.That(SlaveManager.BoatSpawnForwardDot(caster, 0f, ahead)).IsGreaterThan(0.9f);
    }

    [Test]
    public async Task ForwardDot_BehindIsNegative()
    {
        var caster = new Vector3(0f, 0f, 100f);
        var behind = new Vector3(0f, -10f, 100f);
        await Assert.That(SlaveManager.BoatSpawnForwardDot(caster, 0f, behind)).IsLessThan(-0.9f);
    }

    [Test]
    public async Task SurfaceAboveCaster_RejectedAsSkyLake()
    {
        await Assert.That(SlaveManager.IsBoatSurfaceAllowed(
            casterZ: 120f, surfaceZ: 200f, floorZ: 150f, minDepth: 5f)).IsFalse();
    }

    [Test]
    public async Task DeepWaterNearCaster_Allowed()
    {
        await Assert.That(SlaveManager.IsBoatSurfaceAllowed(
            casterZ: 120f, surfaceZ: 100f, floorZ: 80f, minDepth: 5f)).IsTrue();
    }

    [Test]
    public async Task OceanWhileSlightlyUnderSurface_Allowed()
    {
        // Swimming: caster Z can sit below the ocean plane.
        await Assert.That(SlaveManager.IsBoatSurfaceAllowed(
            casterZ: 95f, surfaceZ: 100f, floorZ: 80f, minDepth: 5f)).IsTrue();
    }

    [Test]
    public async Task ShallowWater_Rejected()
    {
        await Assert.That(SlaveManager.IsBoatSurfaceAllowed(
            casterZ: 120f, surfaceZ: 100f, floorZ: 98f, minDepth: 5f)).IsFalse();
    }

    [Test]
    public async Task Score_PrefersAheadOverBehind()
    {
        var ahead = SlaveManager.ScoreBoatSpawnCandidate(1f, 10f, 10f);
        var behind = SlaveManager.ScoreBoatSpawnCandidate(-1f, 10f, 10f);
        await Assert.That(ahead).IsGreaterThan(behind);
    }
}
