using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxSessionsTests
{
    [Test]
    public async Task DisconnectedCachedAvatarDoesNotCountAsAnActiveSession()
    {
        var cached = new Character(null) { Id = 1001, AccountId = 1, Name = "Sandbox" };
        await Assert.That(MechanicsSandboxSessions.Find("Sandbox", [])).IsNull();
        await Assert.That(MechanicsSandboxSessions.IsCurrent(cached, [])).IsFalse();
    }

    [Test]
    public async Task ReconnectResolvesTheNewActorEvenWhenTheCachedActorHasTheSameIdentity()
    {
        var old = new Character(null) { Id = 1001, AccountId = 1, Name = "Sandbox" };
        var current = new Character(null) { Id = 1001, AccountId = 1, Name = "Sandbox" };
        GameConnection[] live = [new(null), new(null) { ActiveChar = current }];
        await Assert.That(ReferenceEquals(MechanicsSandboxSessions.Find("Sandbox", live), current)).IsTrue();
        await Assert.That(MechanicsSandboxSessions.IsCurrent(old, live)).IsFalse();
        await Assert.That(MechanicsSandboxSessions.IsCurrent(current, live)).IsTrue();
        await Assert.That(MechanicsSandboxSessions.Find("sandbox", live)).IsNull();
    }
}
