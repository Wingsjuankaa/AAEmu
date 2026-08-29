using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingRebuildNamePolicyTests
{
    [Test]
    public async Task DefaultSourceName_ChangesToTargetDefault()
    {
        var result = HousingRebuildNamePolicy.ResolveTransition(
            "Thatched Farmhouse",
            "Thatched Farmhouse",
            "Rancher's Farmhouse");

        await Assert.That(result).IsEqualTo("Rancher's Farmhouse");
    }

    [Test]
    public async Task CustomName_IsPreservedAcrossRebuild()
    {
        var result = HousingRebuildNamePolicy.ResolveTransition(
            "Dennia's Farm",
            "Thatched Farmhouse",
            "Miner's Farmhouse");

        await Assert.That(result).IsEqualTo("Dennia's Farm");
    }

    [Test]
    public async Task LoadedLegacySourceDefault_IsNormalizedForExistingTarget()
    {
        var result = HousingRebuildNamePolicy.ResolveLoadedLegacyDefault(
            "Thatched Farmhouse",
            "Rancher's Farmhouse",
            new HashSet<string>(StringComparer.Ordinal) { "Thatched Farmhouse" });

        await Assert.That(result).IsEqualTo("Rancher's Farmhouse");
    }

    [Test]
    public async Task LoadedCustomName_IsNotTreatedAsLegacyDefault()
    {
        var result = HousingRebuildNamePolicy.ResolveLoadedLegacyDefault(
            "Dennia's Farm",
            "Rancher's Farmhouse",
            new HashSet<string>(StringComparer.Ordinal) { "Thatched Farmhouse" });

        await Assert.That(result).IsEqualTo("Dennia's Farm");
    }
}
