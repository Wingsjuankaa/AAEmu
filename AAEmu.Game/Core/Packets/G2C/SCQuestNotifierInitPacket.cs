using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Finalizes the client's quest-notifier state after active and completed quests are sent.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value. The native packet callback dispatches client UI event 0x2A4,
/// rebuilding quest-target markers after the active and completed quest lists are loaded.
/// </remarks>
public class SCQuestNotifierInitPacket(bool init) : GamePacket(SCOffsets.SCQuestNotifierInitPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(init);
        return stream;
    }
}
