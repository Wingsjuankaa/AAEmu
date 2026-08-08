using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSSpecialtyRatioPacket() : GamePacket(CSOffsets.CSSpecialtyRatioPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var id = stream.ReadUInt32();

        var ratio = SpecialtyManager.Instance.GetRatioForSpecialty(Connection.ActiveChar);
        Connection.ActiveChar.SendPacket(new SCSpecialtyRatioPacket(ratio));
    }
}
