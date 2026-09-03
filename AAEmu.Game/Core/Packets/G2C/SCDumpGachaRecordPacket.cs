using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 diagnostic snapshot of one character's persisted Gacha record.</summary>
public class SCDumpGachaRecordPacket(
    uint glpId,
    uint totalCount,
    IReadOnlyCollection<GachaAdvancedRecordEntry> advancedRecords)
    : GamePacket(SCOffsets.SCDumpGachaRecordPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        var records = (advancedRecords ?? []).Take(10).ToArray();
        stream.Write((uint)records.Length);
        stream.Write(glpId);
        stream.Write(totalCount);
        foreach (var record in records)
        {
            stream.Write(record.GachaAdvancedLootPackId);
            stream.Write(record.LastRound);
        }
        return stream;
    }
}

public readonly record struct GachaAdvancedRecordEntry(uint GachaAdvancedLootPackId, uint LastRound);
