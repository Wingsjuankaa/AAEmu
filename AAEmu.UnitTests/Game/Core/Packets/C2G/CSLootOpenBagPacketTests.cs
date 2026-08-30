using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.DoodadObj;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSLootOpenBagPacketTests
{
    [Test]
    public async Task HousingBinding_IsNotDeletedAfterCyclicLootPhase()
    {
        var binding = new Doodad
        {
            OwnerType = DoodadOwnerType.Housing,
            OwnerDbId = 16
        };

        await Assert.That(
            CSLootOpenBagPacket.ShouldDeleteAfterFuncDrivenLoot(binding, remainsLootDriven: false)).IsFalse();
    }

    [Test]
    public async Task OneShotWorldDoodad_IsDeletedAfterLeavingLootPhase()
    {
        var worldDoodad = new Doodad
        {
            OwnerType = DoodadOwnerType.System,
            OwnerDbId = 0
        };

        await Assert.That(
            CSLootOpenBagPacket.ShouldDeleteAfterFuncDrivenLoot(worldDoodad, remainsLootDriven: false)).IsTrue();
        await Assert.That(
            CSLootOpenBagPacket.ShouldDeleteAfterFuncDrivenLoot(worldDoodad, remainsLootDriven: true)).IsFalse();
    }
}
