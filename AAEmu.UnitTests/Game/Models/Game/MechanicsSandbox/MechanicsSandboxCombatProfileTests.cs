using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxCombatProfileTests
{
    [Test]
    public async Task CombatBuild_ExcludesOnlyTheSelectedSystemPassiveForItsExactActor()
    {
        var config = new MechanicsSandboxConfig { Enabled = true, CombatProfile = true,
            CharacterId = 1001, AccountId = 1, CharacterName = "Sandbox" };
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 1, "Sandbox", 369)).IsTrue();
        foreach (var id in new uint[] { 1, 3, 29, 303, 353, 370 })
            await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 1, "Sandbox", id)).IsFalse();
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1002, 1, "Sandbox", 369)).IsFalse();
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 2, "Sandbox", 369)).IsFalse();
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 1, "Wingsjuanka", 369)).IsFalse();
        config.Enabled = false;
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 1, "Sandbox", 369)).IsFalse();
        config.Enabled = true; config.CombatProfile = false;
        await Assert.That(MechanicsSandboxCombatProfile.Excludes(config, 1001, 1, "Sandbox", 369)).IsFalse();
    }
}
