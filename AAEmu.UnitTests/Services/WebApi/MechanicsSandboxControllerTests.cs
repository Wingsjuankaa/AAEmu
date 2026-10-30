using System.Text.RegularExpressions;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Services.WebApi.Controllers;
using NetCoreServer;
using Newtonsoft.Json.Linq;

namespace AAEmu.UnitTests.Services.WebApi;

public class MechanicsSandboxControllerTests
{
    private readonly Character _character = new(null) { Id = 1001, AccountId = 1, Name = "Sandbox" };
    private readonly MechanicsSandboxConfig _config = new()
        { Enabled = true, CharacterName = "Sandbox", CharacterId = 1001, AccountId = 1 };
    private int _access = 100;
    private int _executions;
    private int _lookups;
    private string _lastAction;
    private bool _online = true;
    private MechanicsSandboxConfig _proposed;

    private MechanicsSandboxController Create() => new(() => _config,
        _ => { _lookups++; return _online ? _character : null; }, _ => _access,
        (_, action) =>
        {
            _executions++; _lastAction = action;
            return "{\"success\":true,\"state\":\"ready\",\"characterId\":1001,\"attempt\":1,\"dummies\":[123,124,125,126]}";
        }, (_, proposed) =>
        {
            _executions++; _lastAction = "reconfigure"; _proposed = proposed;
            return "{\"success\":true,\"state\":\"resetting\",\"characterId\":1001}";
        }, (_, proposed) =>
        {
            _executions++; _lastAction = "profile"; _proposed = proposed;
            return "{\"success\":true,\"state\":\"validated\",\"characterId\":1001}";
        });

    private HttpResponse Request(string action = "status", string body = "{\"character\":\"Sandbox\"}")
    {
        var path = "/api/mechanics-sandbox/" + action;
        var request = new HttpRequest("POST", path, "HTTP/1.1");
        request.SetBody(body);
        return Create().Execute(request, Regex.Matches(path, "^/api/mechanics-sandbox/(begin|status|reset|clear|reconfigure|validate)$"));
    }

    [Test]
    [Arguments("begin")]
    [Arguments("status")]
    [Arguments("reset")]
    [Arguments("clear")]
    [Arguments("validate")]
    public async Task TypedActions_ReturnStructuredSnapshotWithoutAChatCommandEnvelope(string action)
    {
        var response = Request(action);
        var snapshot = JObject.Parse(response.Body);
        await Assert.That(response.Status).IsEqualTo(200);
        await Assert.That(snapshot.Value<bool>("success")).IsTrue();
        await Assert.That(snapshot.Value<uint>("characterId")).IsEqualTo(1001u);
        await Assert.That(((JArray)snapshot["dummies"]).Count).IsEqualTo(4);
        await Assert.That(snapshot.ContainsKey("Messages")).IsFalse();
        await Assert.That(_executions).IsEqualTo(1);
        await Assert.That(_lastAction).IsEqualTo(action);
    }

    [Test]
    public async Task DisabledOrDifferentCharacterRequest_CannotLookupOrExecuteAnything()
    {
        _config.Enabled = false;
        await Assert.That(Request().Status).IsEqualTo(403);
        _config.Enabled = true;
        await Assert.That(Request(body: "{\"character\":\"Dannia\"}").Status).IsEqualTo(403);
        await Assert.That(_lookups).IsEqualTo(0);
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task WrongAccountOrInsufficientGmAccess_IsRejectedBeforeManagerMutation()
    {
        _character.AccountId = 2;
        await Assert.That(Request("reset").Status).IsEqualTo(403);
        _character.AccountId = 1; _access = 99;
        await Assert.That(Request("reset").Status).IsEqualTo(403);
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task MalformedJsonOrUnknownAction_IsRejectedWithoutLookup()
    {
        await Assert.That(Request(body: "{invalid").Status).IsEqualTo(400);
        await Assert.That(Request("delete-everything").Status).IsEqualTo(400);
        await Assert.That(_lookups).IsEqualTo(0);
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task OfflineCharacter_IsAnExplicitTransientConflict()
    {
        _online = false;
        var response = Request("begin");
        await Assert.That(response.Status).IsEqualTo(409);
        await Assert.That(JObject.Parse(response.Body).Value<string>("state")).IsEqualTo("offline");
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task PreflightOnExistingBeginRoute_DispatchesValidationInsteadOfBeginningAScene()
    {
        var response = Request("begin", """{"character":"Sandbox","validateOnly":true}""");
        await Assert.That(response.Status).IsEqualTo(200);
        await Assert.That(_lastAction).IsEqualTo("validate");
        await Assert.That(_executions).IsEqualTo(1);
        _executions = 0;
        await Assert.That(Request("begin", """{"character":"Sandbox","validateOnly":"true"}""").Status).IsEqualTo(400);
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task ProfilePublication_RequiresExplicitValidationAndKeepsSceneMutationSeparate()
    {
        const string candidate = """{"character":"Sandbox","validateOnly":true,"configuration":{"SceneName":"Laboratorio","CharacterId":1001,"AccountId":1}}""";
        await Assert.That(Request("begin", candidate).Status).IsEqualTo(200);
        await Assert.That(_lastAction).IsEqualTo("profile");
        await Assert.That(_proposed.SceneName).IsEqualTo("Laboratorio");
        _executions = 0;
        await Assert.That(Request("reset", candidate).Status).IsEqualTo(400);
        await Assert.That(Request("begin", candidate.Replace("true", "false")).Status).IsEqualTo(400);
        await Assert.That(_executions).IsEqualTo(0);
    }

    [Test]
    public async Task ManualGmStatus_IsHumanReadableSpanishWithoutObjectIdsOrJson()
    {
        var text = global::AAEmu.Game.Scripts.Commands.MechanicsSandbox.HumanMessage(
            "{\"state\":\"ready\",\"attempt\":2,\"dummies\":[123,124,125,126]}");
        await Assert.That(text).IsEqualTo("Escenario listo: 4 muñecos de entrenamiento. Intento 2.");
        await Assert.That(text.Contains('{')).IsFalse();
        await Assert.That(text.Contains("123")).IsFalse();
    }

    [Test]
    public async Task LiveLayoutAdjustment_PreservesConfiguredIdentityAndUsesTheReconfigureConsumer()
    {
        _config.SceneName = "Sala con servicios";
        _config.Services = [new() { TemplateId = 18870, Role = "specializations", Forward = -3, Right = -6 }];
        const string body = """
        {"character":"Sandbox","origin":{"X":502,"Y":38373.5,"Z":129.948,"Rotation":0.25},
         "dummies":[{"Forward":7,"Right":-1},{"Forward":12,"Right":1}]}
        """;
        var response = Request("reconfigure", body);
        await Assert.That(response.Status).IsEqualTo(200);
        await Assert.That(_lastAction).IsEqualTo("reconfigure");
        await Assert.That(_executions).IsEqualTo(1);
        await Assert.That(_proposed.CharacterId).IsEqualTo(1001u);
        await Assert.That(_proposed.AccountId).IsEqualTo(1u);
        await Assert.That(_proposed.ZoneKey).IsEqualTo(_config.ZoneKey);
        await Assert.That(_proposed.DummyTemplateId).IsEqualTo(_config.DummyTemplateId);
        await Assert.That(_proposed.Origin.X).IsEqualTo(502f);
        await Assert.That(_proposed.Dummies.Count).IsEqualTo(2);
        await Assert.That(_proposed.SceneName).IsEqualTo(_config.SceneName);
        await Assert.That(_proposed.Services[0].TemplateId).IsEqualTo(18870u);
        _proposed.Services[0].Forward = 20;
        await Assert.That(_config.Services[0].Forward).IsEqualTo(-3f);
    }

    [Test]
    public async Task LiveLayoutAdjustment_RejectsIdentityBalanceFieldsAndMalformedPositionsWithoutMutation()
    {
        const string identityChange = """
        {"character":"Sandbox","accountId":2,"origin":{},"dummies":[{"Forward":7}]}
        """;
        const string balanceChange = """
        {"character":"Sandbox","origin":{},"dummies":[{"Forward":7,"hp":1000000}]}
        """;
        const string malformed = """
        {"character":"Sandbox","origin":{},"dummies":[null]}
        """;
        await Assert.That(Request("reconfigure", identityChange).Status).IsEqualTo(400);
        await Assert.That(Request("reconfigure", balanceChange).Status).IsEqualTo(400);
        await Assert.That(Request("reconfigure", malformed).Status).IsEqualTo(400);
        await Assert.That(_executions).IsEqualTo(0);
        await Assert.That(_config.AccountId).IsEqualTo(1u);
    }
}
