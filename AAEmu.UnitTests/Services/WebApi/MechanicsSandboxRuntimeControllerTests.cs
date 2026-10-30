using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Services.WebApi.Controllers;
using NetCoreServer;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Services.WebApi;

public class MechanicsSandboxRuntimeControllerTests
{
    private static MechanicsSandboxConfig Bound() => new()
    {
        Enabled = true, CharacterId = 1001, AccountId = 1, CharacterName = "Sandbox"
    };

    [Test]
    public async Task DisabledOrUnboundSandbox_DoesNotReadRuntimeDiagnostics()
    {
        MechanicsSandboxConfig[] configurations =
        [new(), new() { Enabled = true }, new() { Enabled = true, CharacterId = 1001, AccountId = 1 }];
        configurations[2].CharacterName = "";
        foreach (var config in configurations)
        {
            var controller = new MechanicsSandboxRuntimeController(() => config, () => "127.0.0.1",
                () => throw new InvalidOperationException("Must not observe ordinary runtime"));
            var result = controller.Runtime(new HttpRequest());
            await Assert.That(result.Status).IsEqualTo(403);
        }
    }

    [Test]
    public async Task NonLoopbackListener_CannotExposeRuntimeDiagnostics()
    {
        foreach (var host in new[] { "*", "0.0.0.0", "::", "192.168.1.94", "localhost" })
        {
            var controller = new MechanicsSandboxRuntimeController(Bound, () => host,
                () => throw new InvalidOperationException("Nonlocal listener must be rejected"));
            await Assert.That(controller.Runtime(new HttpRequest()).Status).IsEqualTo(403);
        }
    }

    [Test]
    public async Task LocalBoundSandbox_ExposesStructuredSnapshotWithoutChatOrSecrets()
    {
        var at = DateTimeOffset.Parse("2026-10-29T22:00:00Z");
        var controller = new MechanicsSandboxRuntimeController(Bound, () => "::1",
            () => new MechanicsSandboxHotReload.RuntimeStatus(42, true, true, 3, at,
                "aa10-real-runtime-v1", ".NET 10.0"));
        var result = controller.Runtime(new HttpRequest());
        var json = JObject.Parse(result.Body);
        await Assert.That(result.Status).IsEqualTo(200);
        await Assert.That(json.Value<int>("pid")).IsEqualTo(42);
        await Assert.That(json.Value<long>("updateCount")).IsEqualTo(3L);
        await Assert.That(json.Value<bool>("hotReloadSupported")).IsTrue();
        await Assert.That(json.Value<bool>("runningUnderWatch")).IsTrue();
        await Assert.That(json.Value<string>("diagnosticStamp")).IsEqualTo("aa10-real-runtime-v1");
        await Assert.That(json.Value<string>("runtimeVersion")).IsEqualTo(".NET 10.0");
        await Assert.That(json["lastUpdateUtc"].ToObject<DateTimeOffset>()).IsEqualTo(at);
        foreach (var privateField in new[] { "token", "password", "credentials", "Messages", "messages" })
            await Assert.That(json.ContainsKey(privateField)).IsFalse();
    }
}
