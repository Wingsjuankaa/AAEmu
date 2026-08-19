using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSSaveUIDataPacket() : GamePacket(CSOffsets.CSSaveUIDataPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var uiDataType = stream.ReadUInt16();
        var id = stream.ReadUInt32();
        var data = stream.ReadString();

        // The client flushes several UI options after SCLeaveWorldGranted. At that point the
        // connection intentionally has no ActiveChar; late teardown packets are safe to ignore.
        Connection.ActiveChar?.SetOption(uiDataType, data);
    }
}
