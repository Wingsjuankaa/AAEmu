using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class HarvestCastTimePolicyTests
{
    [Test]
    public async Task ApplyRate_HarvestAtTenX_ReducesTwelveSecondsToTwelveHundredMilliseconds()
    {
        await Assert.That(HarvestCastTimePolicy.ApplyRate(12_000, 10d)).IsEqualTo(1_200);
    }

    [Test]
    [Arguments(0d)]
    [Arguments(-1d)]
    [Arguments(double.NaN)]
    [Arguments(double.PositiveInfinity)]
    public async Task ApplyRate_InvalidConfiguration_PreservesNativeCast(double rate)
    {
        await Assert.That(HarvestCastTimePolicy.ApplyRate(12_000, rate)).IsEqualTo(12_000);
    }

    [Test]
    public async Task NativeHarvestTransition_RequiresLootOnlyNextPhase()
    {
        var use = new DoodadFuncUse { SkillId = 23480 };
        var transition = new DoodadFunc { NextPhase = 20, FuncType = nameof(DoodadFuncUse) };
        DoodadFunc[] lootOnly =
        [
            new() { FuncType = nameof(DoodadFuncLootPack) },
            new() { FuncType = nameof(DoodadFuncLootItem) }
        ];
        DoodadFunc[] feedNextPhase =
        [
            new() { FuncType = nameof(DoodadFuncUse) }
        ];

        await Assert.That(
            HarvestCastTimePolicy.IsNativeHarvestTransition(transition, use, lootOnly)).IsTrue();
        await Assert.That(
            HarvestCastTimePolicy.IsNativeHarvestTransition(transition, use, feedNextPhase)).IsFalse();
        await Assert.That(
            HarvestCastTimePolicy.IsNativeHarvestTransition(transition, use, Array.Empty<DoodadFunc>())).IsFalse();
    }
}
