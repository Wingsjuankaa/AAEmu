using AAEmu.Game.Models.Game.DoodadObj.Funcs;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class DoodadFuncUseTests
{
    [Test]
    public async Task ShouldScheduleSkill_SuppressesIdenticalInteractionRecursion()
    {
        await Assert.That(DoodadFuncUse.ShouldScheduleSkill(41999, 41999)).IsFalse();
        await Assert.That(DoodadFuncUse.ShouldScheduleSkill(0, 41999)).IsTrue();
        await Assert.That(DoodadFuncUse.ShouldScheduleSkill(41925, 0)).IsFalse();
    }
}
