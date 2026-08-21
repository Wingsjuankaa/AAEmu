using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCServerInfoPacket(long serverOpenTime) : GamePacket(SCOffsets.SCServerInfoPacket, 1)
{
    // Native x2game stores this u64 at ClientPlayer+16000. GetWorldLevelHardCapInfo subtracts it
    // from the current time and selects world_level_hard_caps by elapsed server days. It therefore
    // has to be the stable shard opening time, never the current process/login time.
    public SCServerInfoPacket() : this(AppConfiguration.Instance.InitialConfig.ServerOpenTimeUnixSeconds) { }

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(serverOpenTime);
        return stream;
    }
}
