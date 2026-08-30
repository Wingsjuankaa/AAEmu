using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj.Funcs;

public class DoodadFuncLootPackTests
{
    [Test]
    public async Task ApplyLootResult_AdvancesOnlyAfterRewardWasGranted()
    {
        var doodad = new Doodad { ToNextPhase = true };

        DoodadFuncLootPack.ApplyLootResult(doodad, granted: false);
        await Assert.That(doodad.ToNextPhase).IsFalse();

        DoodadFuncLootPack.ApplyLootResult(doodad, granted: true);
        await Assert.That(doodad.ToNextPhase).IsTrue();
    }
}
