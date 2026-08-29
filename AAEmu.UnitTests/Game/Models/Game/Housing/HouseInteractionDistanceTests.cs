using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HouseInteractionDistanceTests
{
    [Test]
    public async Task HouseDistanceIsMeasuredFromTheDemonstratedHousingFootprint()
    {
        var source = new BaseUnit();
        source.Transform.Local.SetPosition(0f, 0f, 0f);

        var house = new House
        {
            Template = new HousingTemplate { GardenRadius = 11f }
        };
        house.Transform.Local.SetPosition(14.9f, 0f, 0f);

        await Assert.That(source.GetDistanceTo(house, true)).IsBetween(3.89f, 3.91f);
    }

    [Test]
    public async Task HouseFootprintDoesNotAuthorizeRemoteInteraction()
    {
        var source = new BaseUnit();
        source.Transform.Local.SetPosition(0f, 0f, 0f);

        var house = new House
        {
            Template = new HousingTemplate { GardenRadius = 11f }
        };
        house.Transform.Local.SetPosition(15.1f, 0f, 0f);

        await Assert.That(source.GetDistanceTo(house, true)).IsGreaterThan(4f);
    }
}
