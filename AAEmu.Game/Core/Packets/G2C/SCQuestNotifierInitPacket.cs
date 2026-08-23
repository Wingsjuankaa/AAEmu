using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Refreshes the client's quest-notifier UI after active quests are synchronized.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value. The native packet callback ignores the boolean and dispatches
/// client UI event 0x2A4. Native overhead target markers are built by the SCQuests handler and are
/// independent of this event.
/// </remarks>
public class SCQuestNotifierInitPacket(bool init) : GamePacket(SCOffsets.SCQuestNotifierInitPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(init);
        return stream;
    }
}
