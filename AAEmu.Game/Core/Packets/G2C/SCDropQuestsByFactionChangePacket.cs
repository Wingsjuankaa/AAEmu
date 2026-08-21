using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Sends one native AA10 faction-change quest-drop batch (maximum 20 quest ids).
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class SCDropQuestsByFactionChangePacket(bool endList, IReadOnlyList<uint> questIds) : GamePacket(SCOffsets.SCDropQuestsByFactionChangePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        var count = Math.Min(questIds?.Count ?? 0, 20);
        stream.Write(endList);
        stream.Write((uint)count);
        for (var i = 0; i < count; i++)
            stream.Write(questIds[i]);
        return stream;
    }
}
