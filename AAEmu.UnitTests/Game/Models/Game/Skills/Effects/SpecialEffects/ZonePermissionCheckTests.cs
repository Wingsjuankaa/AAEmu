using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Effects.SpecialEffects;

public class ZonePermissionCheckTests
{
    [Test]
    [Arguments(1006, 378u)]
    [Arguments(1008, 378u)]
    [Arguments(1009, 378u)]
    [Arguments(1010, 382u)]
    [Arguments(1013, 382u)]
    public async Task PublicDoors_ResolveOnlyAuthoredDestinations(int point, uint zone)
    {
        var resolved = ZonePermissionCheck.GetPublicReturnPoint(true, 149, point, 55, 8000);
        await Assert.That(resolved).IsEqualTo((uint)point);
        await Assert.That(ZonePermissionCheck.GetAuthoredDestinationZone(resolved)).IsEqualTo(zone);
        await Assert.That(SpecialEffect.IsImplemented(SpecialType.ZonePermissionCheck)).IsTrue();
    }

    [Test]
    [Arguments(false, 149, 1008, 55, 8000)]
    [Arguments(true, 148, 1008, 55, 8000)]
    [Arguments(true, 149, 1005, 55, 8000)]
    [Arguments(true, 149, -1, 55, 8000)]
    [Arguments(true, 149, 1008, 54, 8000)]
    [Arguments(true, 149, 1008, 55, 7999)]
    public async Task InvalidPolicyOrRequirements_Reject(bool enabled, int selector, int point, int level, int gear)
    {
        await Assert.That(ZonePermissionCheck.GetPublicReturnPoint(enabled, selector, point, level, gear)).IsEqualTo(0u);
    }
}
