using System.Net;
using System.Text.RegularExpressions;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using NetCoreServer;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AAEmu.Game.Services.WebApi.Controllers;

/// <summary>Internal sandbox control; polling never goes through the in-game command/chat transport.</summary>
internal sealed class MechanicsSandboxController : BaseController
{
    private readonly Func<MechanicsSandboxConfig> _configuration;
    private readonly Func<string, Character> _find;
    private readonly Func<Character, int> _access;
    private readonly Func<Character, string, string> _execute;
    private readonly Func<Character, MechanicsSandboxConfig, string> _reconfigure;
    private readonly Func<Character, MechanicsSandboxConfig, string> _profile;

    public MechanicsSandboxController() : this(
        () => AppConfiguration.Instance.MechanicsSandbox,
        name => MechanicsSandboxSessions.Find(name, GameConnectionTable.Instance.GetConnections()),
        character => CharacterManager.Instance.GetEffectiveAccessLevel(character),
        (character, action) => MechanicsSandboxManager.Instance.Execute(character, action),
        (character, configuration) => MechanicsSandboxManager.Instance.Reconfigure(character, configuration)) { }

    internal MechanicsSandboxController(Func<MechanicsSandboxConfig> configuration, Func<string, Character> find,
        Func<Character, int> access, Func<Character, string, string> execute,
        Func<Character, MechanicsSandboxConfig, string> reconfigure = null)
        : this(configuration, find, access, execute, reconfigure, null) { }

    internal MechanicsSandboxController(Func<MechanicsSandboxConfig> configuration, Func<string, Character> find,
        Func<Character, int> access, Func<Character, string, string> execute,
        Func<Character, MechanicsSandboxConfig, string> reconfigure,
        Func<Character, MechanicsSandboxConfig, string> profile)
    {
        _configuration = configuration;
        _find = find;
        _access = access;
        _execute = execute;
        _reconfigure = reconfigure;
        _profile = profile;
    }

    [WebApiPost("^/api/mechanics-sandbox/(begin|status|reset|clear|reconfigure|validate)$")]
    public HttpResponse Execute(HttpRequest request, MatchCollection matches)
    {
        if (matches.Count != 1 || matches[0].Groups.Count < 2)
            return Rejected(HttpStatusCode.BadRequest, "Acción de sandbox no válida.");
        var action = matches[0].Groups[1].Value;
        if (action is not ("begin" or "status" or "reset" or "clear" or "reconfigure" or "validate"))
            return Rejected(HttpStatusCode.BadRequest, "Acción de sandbox no válida.");
        JObject body;
        try { body = JObject.Parse(request.Body); }
        catch (JsonException) { return Rejected(HttpStatusCode.BadRequest, "El cuerpo de la solicitud no es JSON válido."); }
        var config = _configuration();
        if (config is not { Enabled: true } || config.CharacterId == 0 || config.AccountId == 0)
            return Rejected(HttpStatusCode.Forbidden, "El sandbox no está habilitado y vinculado en este entorno.");
        if (body["character"]?.Type != JTokenType.String ||
            !string.Equals(body.Value<string>("character"), config.CharacterName, StringComparison.Ordinal))
            return Rejected(HttpStatusCode.Forbidden, "La solicitud no corresponde al personaje exclusivo del sandbox.");
        var character = _find(config.CharacterName);
        if (character == null)
            return Rejected(HttpStatusCode.Conflict, "El personaje del sandbox todavía no está conectado.", "offline");
        if (character.Id != config.CharacterId || character.AccountId != config.AccountId ||
            !string.Equals(character.Name, config.CharacterName, StringComparison.Ordinal) || _access(character) < 100)
            return Rejected(HttpStatusCode.Forbidden, "La identidad o el acceso del personaje no autoriza esta operación.");
        if (body["validateOnly"] != null && body["validateOnly"].Type != JTokenType.Boolean)
            return Rejected(HttpStatusCode.BadRequest, "validateOnly debe ser booleano.");
        // Uses an already registered route while the development host is hot-reloading new metadata.
        if (action == "begin" && body.Value<bool?>("validateOnly") == true)
            action = "validate";
        if (body["configuration"] != null)
        {
            if (action != "validate" || body["configuration"] is not JObject configuration)
                return Rejected(HttpStatusCode.BadRequest, "El perfil sólo se publica mediante validación explícita.");
            MechanicsSandboxConfig proposed;
            try { proposed = configuration.ToObject<MechanicsSandboxConfig>(); }
            catch (JsonException) { return Rejected(HttpStatusCode.BadRequest, "El perfil no tiene un formato válido."); }
            // A pre-Hot Reload controller instance has no newly added delegate field yet.
            var publish = _profile ?? MechanicsSandboxManager.Instance.ConfigureProfile;
            return OkJson(JObject.Parse(publish(character, proposed)));
        }
        if (action == "reconfigure")
        {
            if (body.Properties().Any(property => property.Name is not ("character" or "origin" or "dummies")) ||
                body["origin"] is not JObject origin || body["dummies"] is not JArray dummies ||
                dummies.Count is < 1 or > 16 ||
                origin.Properties().Any(property => property.Name.ToLowerInvariant() is not ("x" or "y" or "z" or "rotation")) ||
                dummies.Any(dummy => dummy is not JObject position || position.Properties().Any(property =>
                    property.Name.ToLowerInvariant() is not ("forward" or "right" or "up"))) || _reconfigure == null)
                return Rejected(HttpStatusCode.BadRequest, "Sólo se admiten el origen y las posiciones de los dummies.");
            MechanicsSandboxConfig proposed;
            try
            {
                proposed = new MechanicsSandboxConfig
                {
                    Enabled = config.Enabled, CombatProfile = config.CombatProfile, CharacterId = config.CharacterId, CharacterName = config.CharacterName,
                    AccountId = config.AccountId, WorldId = config.WorldId, InstanceId = config.InstanceId,
                    ZoneKey = config.ZoneKey, DummyTemplateId = config.DummyTemplateId,
                    SceneName = config.SceneName,
                    Services = config.Services.Select(service => new MechanicsSandboxServiceNpc
                    { TemplateId = service.TemplateId, Role = service.Role, Forward = service.Forward,
                      Right = service.Right, Up = service.Up, Rotation = service.Rotation }).ToList(),
                    Origin = body["origin"].ToObject<MechanicsSandboxOrigin>(),
                    Dummies = body["dummies"].ToObject<List<MechanicsSandboxDummy>>()
                };
            }
            catch (JsonException) { return Rejected(HttpStatusCode.BadRequest, "Las posiciones no tienen un formato válido."); }
            return OkJson(JObject.Parse(_reconfigure(character, proposed)));
        }
        // JObject prevents a double-encoded JSON string; no IMessageOutput or SendMessage is involved.
        return OkJson(JObject.Parse(_execute(character, action)));
    }

    private static HttpResponse Rejected(HttpStatusCode status, string message, string state = "rejected") =>
        JsonResponse(status, new { success = false, state, message });
}
