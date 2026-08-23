using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Game.World.Zones;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class SubZoneManagerTests
{
    [Test]
    public void Load_CallsGetWorldTemplates()
    {
        var mockWorld = Mock.Of<IWorldManager>();
        mockWorld.GetWorldTemplates().Returns([]);
        var manager = new SubZoneManager(mockWorld.Object, Mock.Of<IZoneManager>().Object);
        manager.Load();

        mockWorld.GetWorldTemplates().WasCalled(Times.Once);
    }

    [Test]
    public async Task GetSubZoneByPosition_UsesZoneKeyIndex()
    {
        const uint zoneKey = 206;
        const uint subZoneId = 42;
        var world = new WorldTemplate
        {
            Id = 0,
            SubZones =
            {
                [zoneKey] =
                [
                    new Area
                    {
                        Id = subZoneId,
                        _points =
                        [
                            new Point(0, 0, 0),
                            new Point(10, 0, 0),
                            new Point(10, 10, 0),
                            new Point(0, 10, 0)
                        ]
                    }
                ]
            }
        };
        var mockWorld = Mock.Of<IWorldManager>();
        mockWorld.GetZoneId(world, 5, 5).Returns(zoneKey);
        var manager = new SubZoneManager(mockWorld.Object, Mock.Of<IZoneManager>().Object);

        var result = manager.GetSubZoneByPosition(world, 5, 5);

        await Assert.That(result).IsEquivalentTo([subZoneId]);
    }

}
