using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Core.Packets.G2C;

/// <remarks>
/// The native serializer names these u32 fields zoneId/state. The r575 handler compares their
/// combined 64 bits against its stored ZoneInstanceId, so state carries the dynamic instance id.
/// </remarks>
public class SCProcessingInstancePacket(ZoneInstanceId zoneInstanceId) : GamePacket(SCOffsets.SCProcessingInstancePacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(zoneInstanceId.ZoneId);
        stream.Write(zoneInstanceId.InstanceId);
        return stream;
    }
}
