using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSCancelInstantGamePacketTests
{
    [Test]
    public async Task TryCancelDungeonInvitation_RoutesUntimedRejectionToIndunManager()
    {
        var character = new Character(new UnitCustomModelParams());
        var indunManager = Mock.Of<IIndunManager>();
        indunManager.RespondToDungeonInvitation(character, false, Any<int?>()).Returns(true);

        var result = CSCancelInstantGamePacket.TryCancelDungeonInvitation(
            character,
            indunManager.Object);

        await Assert.That(result).IsTrue();
    }

    [Test]
    public async Task TryCancelDungeonInvitation_RejectsMissingCharacter()
    {
        var indunManager = Mock.Of<IIndunManager>();

        var result = CSCancelInstantGamePacket.TryCancelDungeonInvitation(
            null,
            indunManager.Object);

        await Assert.That(result).IsFalse();
        Mock.VerifyNoOtherCalls(indunManager);
    }
}
