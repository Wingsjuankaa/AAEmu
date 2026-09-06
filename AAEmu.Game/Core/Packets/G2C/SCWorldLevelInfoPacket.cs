using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

// SC_PACKET_WORLD_LEVEL_INFO (906). Carries the world-level state the client's player-frame gauge reads to render
// the world-level-vs-character-level indicator. Values still mirror the reference world-entry capture;
// this is not a reconstructed dynamic producer. Native serializer RVA 0xA95630 identifies all six fields.
// The handler RVA 0x346880 stores worldLevel and emits WORLDLEVEL_CHANGED; the HUD derives the remaining
// displayed information independently from the character, server-open timestamp and native catalogue.
public class SCWorldLevelInfoPacket() : GamePacket(SCOffsets.SCWorldLevelInfoPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(42u);          // worldLevel
        stream.Write(6u);           // serverDays (captured; not grade)
        stream.Write(10000u);       // expModifier, in 1/100 percent units
        stream.Write(0u);           // hardCapLevel
        stream.Write(1u);           // characterLevel (not an enabled flag)
        stream.Write(unchecked((uint)-41)); // signed levelDiff: characterLevel - worldLevel
        return stream;
    }
}
