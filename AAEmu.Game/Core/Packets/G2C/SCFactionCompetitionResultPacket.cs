using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.FactionCompetition;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 serializer: zone-group u16, winning faction i32, vector count i32.</summary>
public sealed class SCFactionCompetitionResultPacket(
    ushort zoneGroupId,
    int winnerFactionId,
    IReadOnlyList<FactionCompetitionPoint> points)
    : GamePacket(SCOffsets.SCFactionCompetitionResultPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(zoneGroupId);
        stream.Write(winnerFactionId);
        var rows = points ?? Array.Empty<FactionCompetitionPoint>();
        stream.Write(rows.Count);
        foreach (var row in rows)
            row.Write(stream);
        return stream;
    }
}
