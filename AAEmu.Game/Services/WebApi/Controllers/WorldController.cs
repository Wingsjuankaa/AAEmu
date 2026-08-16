using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Services.WebApi.Models;
using AAEmu.Game.Core.Managers;
using NetCoreServer;

namespace AAEmu.Game.Services.WebApi.Controllers;

/// <summary>
/// Character controller for the WebApi
/// </summary>6
internal class WorldController : BaseController
{
    [WebApiGet("/api/world/logged-characters")]
    public HttpResponse GetCharacter(HttpRequest request)
    {
        var loggedCharacters = WorldManager.Instance.GetAllCharacters()
            .Select(x => new CharacterModel(x.Id, x.Name, x.Level, x.Created, x.IsOnline));
        return OkJson(loggedCharacters);
    }

    [WebApiGet("/api/world/zone-manager-status")]
    public HttpResponse GetZoneManagerStatus(HttpRequest request)
    {
        var players = WorldManager.Instance.GetAllCharacters()
            .Where(character => character.IsOnline)
            .Select(character =>
            {
                var zoneKey = character.Transform?.ZoneId ?? 0;
                var zone = ZoneManager.Instance.GetZoneByKey(zoneKey);
                // World position drives the Zone Manager's proximity pre-start: a zone is brought
                // up while the nearest player is still short of its border, not on arrival.
                var position = character.Transform?.World.Position ?? default;
                return new WorldPlayerStatusModel(
                    character.Id,
                    character.ObjId,
                    character.Name,
                    character.Level,
                    zoneKey,
                    zone?.Name ?? "Unknown",
                    character.Transform?.InstanceId ?? 0,
                    position.X,
                    position.Y);
            })
            .OrderBy(character => character.Name)
            .ToArray();

        var zones = WorldIntegration.GetZoneConnectionStatus?.Invoke() ?? [];
        return OkJson(new WorldStatusModel(
            DateTime.UtcNow,
            Program.UpTime,
            players.Length,
            players,
            zones));
    }

    [WebApiGet("/api/world/chat-events")]
    public HttpResponse GetChatEvents(HttpRequest request)
    {
        var query = ParseQueryString(request.Url);
        _ = long.TryParse(query.Get("afterId"), out var afterId);
        var limit = int.TryParse(query.Get("limit"), out var requestedLimit) ? requestedLimit : 200;
        return OkJson(ChatEventJournal.ReadAfter(Math.Max(0, afterId), limit));
    }
}
