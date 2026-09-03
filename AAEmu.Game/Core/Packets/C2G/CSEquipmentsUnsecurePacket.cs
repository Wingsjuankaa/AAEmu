using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSEquipmentsUnsecurePacket() : GamePacket(CSOffsets.CSEquipmentsUnsecurePacket, 1)
{
    public override void Read(PacketStream stream)
    {
        // Empty struct
    }

    public override void Execute() =>
        ItemSecurityService.Instance.UnlockEquipment(Connection?.ActiveChar);
}
