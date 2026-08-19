using AAEmu.Game.Models.Game.Char;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class GmSpeedLevelPolicyTests
{
    [Test]
    [Arguments(0, false)]
    [Arguments(1, true)]
    [Arguments(1000, true)]
    [Arguments(1001, false)]
    public async Task IsValid_EnforcesInclusiveOneToOneThousandRange(int level, bool expected)
    {
        await Assert.That(GmSpeedLevelPolicy.IsValid(level)).IsEqualTo(expected);
    }

    [Test]
    [Arguments(1, 10u, 1.01f)]
    [Arguments(100, 1000u, 2f)]
    [Arguments(1000, 10000u, 11f)]
    public async Task Conversion_MatchesNativeAa10LinearLevelModifier(
        int level,
        uint expectedAbilityLevel,
        float expectedMultiplier)
    {
        await Assert.That(GmSpeedLevelPolicy.ToNativeAbilityLevel(level)).IsEqualTo(expectedAbilityLevel);
        await Assert.That(GmSpeedLevelPolicy.ToMoveSpeedMultiplier(level)).IsEqualTo(expectedMultiplier);
    }
}
