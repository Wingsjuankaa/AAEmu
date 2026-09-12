using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Effects.SpecialEffects;

[NotInParallel]
public class ReturnAvailabilityTests
{
    [Test]
    [Arguments(false, 1005u, 379u)]
    [Arguments(true, 1005u, 379u)]
    [Arguments(false, 1008u, 378u)]
    [Arguments(true, 1008u, 378u)]
    [Arguments(false, 1010u, 382u)]
    [Arguments(true, 1010u, 382u)]
    public async Task GardenReturnWithoutDestinationHost_DoesNotChangeCharacter(bool missingProbe, uint returnPoint, uint zoneId)
    {
        var singleton = typeof(Singleton<PortalManager>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
        var previousManager = singleton.GetValue(null);
        var previousAuthority = WorldIntegration.ZoneAuthority;
        var previousProbe = WorldIntegration.IsZoneLoaded;
        try
        {
            var manager = new PortalManager(Mock.Of<ILocalizationManager>().Object,
                Mock.Of<IWorldManager>().Object, Mock.Of<IZoneManager>().Object,
                Mock.Of<ISubZoneManager>().Object, Mock.Of<INpcManager>().Object,
                Mock.Of<IObjectIdManager>().Object, Mock.Of<ITaskManager>().Object);
            var destinations = (Dictionary<uint, Portal>)typeof(PortalManager)
                .GetField("_nativeReturnDestinationsById", BindingFlags.Instance | BindingFlags.NonPublic)!
                .GetValue(manager)!;
            destinations[returnPoint] = new Portal { Id = returnPoint, ZoneId = zoneId, X = 499.448f, Y = 38375.493f, Z = 131.172f };
            singleton.SetValue(null, manager);
            WorldIntegration.ZoneAuthority = true;
            uint requestedZone = 0;
            WorldIntegration.IsZoneLoaded = missingProbe ? null : zone => { requestedZone = zone; return false; };
            var character = new Character(null) { Id = 1007, DisabledSetPosition = false };
            var originalTransform = character.Transform;

            new Return().Execute(character, null, null, null, null, null, null, DateTime.UtcNow, checked((int)returnPoint), 0, 0, 0);

            await Assert.That(ReferenceEquals(character.Transform, originalTransform)).IsTrue();
            await Assert.That(character.DisabledSetPosition).IsFalse();
            await Assert.That(requestedZone).IsEqualTo(missingProbe ? 0u : zoneId);
        }
        finally
        {
            singleton.SetValue(null, previousManager);
            WorldIntegration.ZoneAuthority = previousAuthority;
            WorldIntegration.IsZoneLoaded = previousProbe;
        }
    }
}
