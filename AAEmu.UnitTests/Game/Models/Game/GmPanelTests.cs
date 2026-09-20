using System.Text;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.GmPanel;

namespace AAEmu.UnitTests.Game.Models.Game;

public class GmPanelTests
{
    private static string Hex(string value) => Convert.ToHexString(Encoding.UTF8.GetBytes(value));
    private readonly Character _character = new(null);
    private readonly List<string> _executed = [];
    private readonly List<(string Kind, string Text)> _responses = [];
    private int _access = 100;
    private bool _online = true;
    private DateTime _now = DateTime.UtcNow;
    private GmPanelService Create() => new(_ => _access, _ => _online,
        access => access >= 100 ? [new("resetcd", "combat", "Reset", "", false, ""), new("scripts", "admin", "Scripts", "", true, "")]
            : [new("resetcd", "combat", "Reset", "", false, "")],
        (_, text) => { _executed.Add(text); return true; },
        (_, _, kind, value) => _responses.Add((kind, value)));
    private void Send(GmPanelService service, uint id, string payload)
    {
        _now = _now.AddSeconds(1);
        var count = (payload.Length + 23) / 24;
        for (var part = 0; part < count; part++)
            service.Receive(_character, $"aa10gm1:{id:x}:{part + 1}:{count}:{payload.Substring(part * 24, Math.Min(24, payload.Length - part * 24))}", "", false, _now);
    }

    [Test]
    public async Task TransportDispatchesExactlyOnceAndPreservesUtf8Arguments()
    {
        var service = Create();
        Send(service, 1, "run/" + Hex("resetcd ñandú"));
        Send(service, 1, "run/" + Hex("resetcd ñandú"));
        await Assert.That(_executed.Count).IsEqualTo(1);
        await Assert.That(_executed[0]).IsEqualTo("resetcd ñandú");
    }

    [Test]
    public async Task RegularPlayersOfflineAndRevokedGmsCannotExecute()
    {
        var service = Create();
        _access = 0; Send(service, 1, "run/" + Hex("resetcd"));
        await Assert.That(_responses.Last().Kind).IsEqualTo("denied");
        _access = 100; _online = false; Send(service, 2, "run/" + Hex("resetcd"));
        _online = true; Send(service, 3, "run/" + Hex("scripts shutdown"));
        _access = 0; Send(service, 4, "confirm/3");
        await Assert.That(_executed.Count).IsEqualTo(0);
    }

    [Test]
    public async Task DangerousCommandRequiresMatchingSingleUseConfirmation()
    {
        var service = Create(); Send(service, 1, "run/" + Hex("scripts shutdown"));
        await Assert.That(_executed.Count).IsEqualTo(0);
        await Assert.That(_responses.Last().Kind).IsEqualTo("confirm");
        Send(service, 2, "confirm/1"); Send(service, 3, "confirm/1");
        await Assert.That(_executed.Count).IsEqualTo(1);
        await Assert.That(_executed[0]).IsEqualTo("scripts shutdown");
    }

    [Test]
    public async Task ConfirmationExpiresAndRechecksCommandPermission()
    {
        var service = Create(); Send(service, 1, "run/" + Hex("scripts shutdown"));
        _now = _now.AddSeconds(21); Send(service, 2, "confirm/1");
        Send(service, 3, "run/" + Hex("scripts shutdown"));
        _access = 50; Send(service, 4, "confirm/3");
        await Assert.That(_executed.Count).IsEqualTo(0);
    }

    [Test]
    public async Task ChangedTargetInvalidatesConfirmation()
    {
        var service = Create(); Send(service, 1, "run/" + Hex("scripts shutdown"));
        _character.CurrentTarget = new Character(null) { ObjId = 42 };
        Send(service, 2, "confirm/1");
        await Assert.That(_executed.Count).IsEqualTo(0);
    }

    [Test]
    public async Task InvalidCommandsNeverDispatch()
    {
        var service = Create(); uint id = 1;
        foreach (var value in new[] { "", "/resetcd", " resetcd", "resetcd\nshutdown", "resetcd\0", new string('x', 131), "unknown" })
            Send(service, id++, "run/" + Hex(value));
        Send(service, id++, "run/zz"); Send(service, id, "run/C0AF");
        await Assert.That(_executed.Count).IsEqualTo(0);
    }

    [Test]
    public async Task EveryCurrentCommandImplementationHasSpanishEditorialMetadata()
    {
        var types = typeof(ICommand).Assembly.GetTypes().Where(t => t is { IsAbstract: false, IsInterface: false } && typeof(ICommand).IsAssignableFrom(t));
        foreach (var type in types)
            await Assert.That(GmPanelDescriptions.Has(type.Name)).IsTrue();
    }
}
