using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSInvitationAnswerPacketTests
{
    [Test]
    public async Task TryHandle_RoutesDungeonAcceptanceToIndunManager()
    {
        var character = new Character(new UnitCustomModelParams());
        var indunManager = Mock.Of<IIndunManager>();
        indunManager.RespondToDungeonInvitation(character, true, 123).Returns(true);

        var result = CSInvitationAnswerPacket.TryHandle(character, indunManager.Object, true, 123);

        await Assert.That(result).IsTrue();
    }

    [Test]
    public async Task TryHandle_PropagatesMissingDungeonInvitation()
    {
        var character = new Character(new UnitCustomModelParams());
        var indunManager = Mock.Of<IIndunManager>();
        indunManager.RespondToDungeonInvitation(character, false, 123).Returns(false);

        var result = CSInvitationAnswerPacket.TryHandle(character, indunManager.Object, false, 123);

        await Assert.That(result).IsFalse();
    }

    [Test]
    public async Task TryHandle_RejectsMissingCharacterWithoutCallingManager()
    {
        var indunManager = Mock.Of<IIndunManager>();

        var result = CSInvitationAnswerPacket.TryHandle(null, indunManager.Object, true, 123);

        await Assert.That(result).IsFalse();
        Mock.VerifyNoOtherCalls(indunManager);
    }
}
