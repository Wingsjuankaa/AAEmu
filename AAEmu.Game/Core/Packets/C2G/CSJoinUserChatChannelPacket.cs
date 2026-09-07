using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSJoinUserChatChannelPacket() : GamePacket(CSOffsets.CSJoinUserChatChannelPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var name = stream.ReadString();
        var pwd = stream.ReadString();
        var create = stream.ReadBoolean();
        if (EquipSlotReinforceBatchTransport.IsReserved(name))
        {
            Connection.ActiveChar?.EquipSlotReinforce?.ReceiveBatchFragment(name, pwd, create);
            return;
        }
        Logger.Debug("JoinUserChatChannel, Name: {0}, Create: {1}", name, create);
    }
}
