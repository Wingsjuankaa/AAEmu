namespace AAEmu.Game.Services.WebApi.Models;

internal sealed record WorldStatusModel(
    DateTime ServerTimeUtc,
    int UptimeSeconds,
    int PlayerCount,
    IReadOnlyList<WorldPlayerStatusModel> Players,
    IReadOnlyList<WorldLoginReservationModel> LoginReservations,
    IReadOnlyList<WorldZoneConnectionSnapshot> Zones);

internal sealed record WorldPlayerStatusModel(
    uint Id,
    uint ObjectId,
    string Name,
    byte Level,
    uint ZoneKey,
    string ZoneName,
    uint InstanceId,
    float X,
    float Y);

internal sealed record WorldLoginReservationModel(
    uint CharacterId,
    string CharacterName,
    uint ZoneKey,
    string ZoneName);
