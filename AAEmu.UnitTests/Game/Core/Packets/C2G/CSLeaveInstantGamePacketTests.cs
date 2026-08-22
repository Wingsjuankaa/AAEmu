using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSLeaveInstantGamePacketTests
{
    [Test]
    public async Task TryLeave_UsesDungeonManagerWhenCharacterIsNotInBattlefield()
    {
        var character = new Character(new UnitCustomModelParams());
        var indunManager = Mock.Of<IIndunManager>();
        indunManager.RequestLeaveInstance(character).Returns(true);

        var result = CSLeaveInstantGamePacket.TryLeave(character, indunManager.Object);

        await Assert.That(result).IsTrue();
    }

    [Test]
    public async Task TryLeave_PropagatesDungeonManagerRejection()
    {
        var character = new Character(new UnitCustomModelParams());
        var indunManager = Mock.Of<IIndunManager>();
        indunManager.RequestLeaveInstance(character).Returns(false);

        var result = CSLeaveInstantGamePacket.TryLeave(character, indunManager.Object);

        await Assert.That(result).IsFalse();
    }

    [Test]
    public async Task TryLeave_RejectsMissingCharacterWithoutCallingManager()
    {
        var indunManager = Mock.Of<IIndunManager>();

        var result = CSLeaveInstantGamePacket.TryLeave(null, indunManager.Object);

        await Assert.That(result).IsFalse();
        Mock.VerifyNoOtherCalls(indunManager);
    }
}
