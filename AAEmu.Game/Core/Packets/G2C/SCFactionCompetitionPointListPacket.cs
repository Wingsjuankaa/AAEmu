using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.FactionCompetition;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 serializer: bool, zone-group u16, start i64, duration i64, vector count i32.</summary>
public sealed class SCFactionCompetitionPointListPacket(
    bool isZoneIn,
    ushort zoneGroupId,
    DateTime startTime,
    long durationSeconds,
    IReadOnlyList<FactionCompetitionPoint> points)
    : GamePacket(SCOffsets.SCFactionCompetitionPointListPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(isZoneIn);
        stream.Write(zoneGroupId);
        stream.Write(startTime);
        stream.Write(durationSeconds);
        var rows = points ?? Array.Empty<FactionCompetitionPoint>();
        stream.Write(rows.Count);
        foreach (var row in rows)
            row.Write(stream);
        return stream;
    }
}
